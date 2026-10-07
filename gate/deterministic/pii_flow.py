"""P2/P3 (AGENTS#1-3): where personal data ends up, by sink.

Static, AST-based taint tracking. Sources are the personal fields (`student.email`,
`payload["email"]`, a variable or parameter named `email`), names assigned from them, calls
to helpers that return them, and whole `Student` objects serialized (`asdict`, `vars`,
`__dict__`, `str`, f-strings). `redact()` sanitizes.

| Sink                                              | Rule      | Severity |
|---------------------------------------------------|-----------|----------|
| logging / print / exception messages              | AGENTS#1  | critical |
| return value of a FastAPI route                   | AGENTS#1  | critical |
| outbound: HTTP clients, SMTP, SDKs, file exports  | AGENTS#2  | critical |
| copy into a module-level collection               | AGENTS#3  | high     |

Taint is tracked inside each function, plus one level of "this helper returns personal
data / a Student" summaries across all service modules. Anything subtler (renamed fields,
derived values) is left to the AI pipeline (B1-B3).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from gate.config import is_service_python, pii_fields
from gate.diff import DiffContext
from gate.report.finding import Finding, Signal

LOG_METHODS = {"debug", "info", "warning", "warn", "error", "exception", "critical", "fatal", "log"}
ROUTE_METHODS = {"get", "post", "put", "patch", "delete", "api_route", "head", "options"}
OUTBOUND_MODULES = {
    "httpx",
    "requests",
    "urllib",
    "urllib3",
    "aiohttp",
    "smtplib",
    "sendgrid",
    "boto3",
    "segment",
    "analytics",
    "mixpanel",
    "amplitude",
    "posthog",
    "sentry_sdk",
    "socket",
}
OUTBOUND_METHODS = {"sendmail", "send_message", "track", "identify", "publish", "capture", "upload"}
FILE_WRITE_METHODS = {"write", "writelines", "write_text", "write_bytes", "to_csv", "to_json"}
FILE_WRITE_FUNCS = {"dump"}  # json.dump, pickle.dump, yaml.dump
COLLECTION_METHODS = {"append", "extend", "add", "insert", "update", "setdefault", "appendleft"}
SERIALIZERS = {"asdict", "vars", "str", "repr", "dict", "jsonable_encoder", "astuple", "dumps"}
STUDENT_FACTORIES = {"_get_student", "get_student", "Student"}
SANITIZERS = {"redact"}
LOG_HANDLERS = {"FileHandler", "HTTPHandler", "SMTPHandler", "SocketHandler", "SysLogHandler", "RotatingFileHandler"}

SINK_RULES = {
    "log": (
        "AGENTS#1",
        "critical",
        "a log/print call",
        'Log only pseudonymous ids: `logger.info("...", redact({...}))` or log `student.id`.',
    ),
    "exception": (
        "AGENTS#1",
        "critical",
        "an exception message",
        "Keep personal data out of error messages; reference `student_id` only.",
    ),
    "response": (
        "AGENTS#1",
        "critical",
        "an API response",
        "Return `student_id` and non-personal fields only; never return personal data in plain text.",
    ),
    "outbound": (
        "AGENTS#2",
        "critical",
        "an outbound call (HTTP/email/SDK/file export)",
        "Send only minimized, pseudonymous data (`student_id`), document the legal basis in the PR, or remove the call.",
    ),
    "persisted": (
        "AGENTS#3",
        "high",
        "a copy stored in a module-level collection",
        "Store `student_id` instead of personal fields, and declare the dataset's category in `RETENTION_DAYS`.",
    ),
}


def _name(node: ast.AST) -> str:
    """Dotted name of a Name/Attribute chain (`self.logger.info` -> 'self.logger.info')."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        return _name(node.func)
    return ""


def _looks_like_student(name: str) -> bool:
    lowered = name.lower()
    return (
        "student" in lowered
        and not lowered.endswith(("_id", "_ids", "id", "_count", "_total", "_len"))
        and not lowered.startswith(("num_", "n_", "total_"))
    )


def _is_route(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr in ROUTE_METHODS
        for d in func.decorator_list
    )


def _own_nodes(body: list[ast.stmt]):
    """Walks statements without descending into nested function/class definitions."""
    stack = list(reversed(body))
    while stack:
        node = stack.pop()
        yield node
        for child in reversed(list(ast.iter_child_nodes(node))):
            if not isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
                stack.append(child)


@dataclass
class Summaries:
    pii_funcs: set[str]
    student_funcs: set[str]
    outbound_names: set[str]
    module_collections: set[str]


class Scope:
    """Taint state of one function (or a module's top-level statements)."""

    def __init__(self, fields: frozenset[str], summaries: Summaries, func=None, body=None):
        self.fields = fields
        self.s = summaries
        self.tainted: set[str] = set()
        self.students: set[str] = set()
        self.body = body if body is not None else func.body
        if func is not None:
            args = func.args
            for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg]:
                if arg is None:
                    continue
                annotation = _name(arg.annotation) if arg.annotation is not None else ""
                if annotation.endswith("Student") or _looks_like_student(arg.arg):
                    self.students.add(arg.arg)
                elif arg.arg in fields:
                    self.tainted.add(arg.arg)
        for _ in range(3):  # flow-insensitive fixed point
            self._propagate()

    # --- classification -----------------------------------------------------------

    def is_student(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self.students or _looks_like_student(node.id)
        if isinstance(node, ast.Call):
            callee = _name(node.func).split(".")[-1]
            if callee in STUDENT_FACTORIES or callee in self.s.student_funcs:
                return True
            return (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and "STUDENTS" in _name(node.func.value)
            )
        if isinstance(node, ast.Subscript):
            return "STUDENTS" in _name(node.value)
        return False

    def exposure(self, node: ast.AST, bare_student: bool = True) -> ast.AST | None:
        """First sub-expression that puts personal data into `node`'s value, or None."""
        if isinstance(node, ast.Call):
            callee = _name(node.func)
            short = callee.split(".")[-1]
            if short in SANITIZERS:
                return None
            if short in self.s.pii_funcs:
                return node
            if (
                short == "getattr"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in self.fields
            ):
                return node
            if short in SERIALIZERS and any(self.is_student(a) for a in node.args):
                return node
            for child in [node.func, *node.args, *[k.value for k in node.keywords]]:
                hit = self.exposure(child, bare_student=False)
                if hit is not None:
                    return hit
            return None
        if isinstance(node, ast.Attribute):
            if node.attr in self.fields:
                return node
            if node.attr == "__dict__" and self.is_student(node.value):
                return node
            return self.exposure(node.value, bare_student=False)
        if isinstance(node, ast.Subscript):
            key = node.slice
            if isinstance(key, ast.Constant) and key.value in self.fields:
                return node
            return self.exposure(node.value, bare_student=False) or self.exposure(key, bare_student=False)
        if isinstance(node, ast.Name):
            if node.id in self.tainted or node.id in self.fields:
                return node
            if bare_student and self.is_student(node):
                return node
            return None
        if isinstance(node, ast.FormattedValue):
            return self.exposure(node.value, bare_student=True)
        if isinstance(node, ast.Lambda):
            return None
        keep_bare = isinstance(
            node, ast.Dict | ast.List | ast.Tuple | ast.Set | ast.JoinedStr | ast.BinOp | ast.IfExp | ast.Starred
        )
        for child in ast.iter_child_nodes(node):
            if isinstance(node, ast.Dict) and child in node.keys:
                continue  # a key named "email" is not the data; the value is
            hit = self.exposure(child, bare_student=bare_student and keep_bare)
            if hit is not None:
                return hit
        return None

    def _propagate(self) -> None:
        for node in _own_nodes(self.body):
            if isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign | ast.NamedExpr):
                value = node.value
                if value is None:
                    continue
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = [n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name)]
                if self.is_student(value):
                    self.students.update(names)
                elif self.exposure(value) is not None:
                    self.tainted.update(names)
            elif isinstance(node, ast.For | ast.AsyncFor | ast.comprehension):
                names = [n.id for n in ast.walk(node.target) if isinstance(n, ast.Name)]
                if "STUDENTS" in ast.unparse(node.iter):
                    self.students.update(names)
                elif self.exposure(node.iter) is not None:
                    self.tainted.update(names)

    # --- sinks ----------------------------------------------------------------------

    def sinks(self, is_route: bool):
        """Yields (kind, sink node, [expressions reaching the sink])."""
        for node in _own_nodes(self.body):
            if isinstance(node, ast.Return) and is_route and node.value is not None:
                yield "response", node, [node.value]
            elif isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
                yield "exception", node, [*node.exc.args, *[k.value for k in node.exc.keywords]]
            elif isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Subscript) and self._is_collection(t.value) for t in node.targets
            ):
                yield "persisted", node, [node.value]
            elif isinstance(node, ast.Call):
                kind = self._call_kind(node)
                if kind:
                    yield kind, node, [*node.args, *[k.value for k in node.keywords]]

    def _is_collection(self, node: ast.AST) -> bool:
        name = _name(node)
        last = name.split(".")[-1]
        return bool(last) and (last in self.s.module_collections or (last.isupper() and len(last) > 1))

    def _call_kind(self, call: ast.Call) -> str | None:
        func = call.func
        dotted = _name(func)
        root, last = dotted.split(".")[0], dotted.split(".")[-1]
        if isinstance(func, ast.Name) and func.id == "print":
            return "log"
        if isinstance(func, ast.Attribute):
            receiver = _name(func.value).lower()
            if func.attr in LOG_METHODS and "log" in receiver:
                return "log"
            if func.attr in COLLECTION_METHODS and self._is_collection(func.value):
                return "persisted"
            if func.attr in FILE_WRITE_METHODS or (
                func.attr in FILE_WRITE_FUNCS and root in {"json", "pickle", "yaml", "marshal"}
            ):
                return "outbound"
        if root in OUTBOUND_MODULES or root in self.s.outbound_names or last in OUTBOUND_METHODS:
            return "outbound"
        return None


COLLECTION_FACTORIES = {"list", "dict", "set", "deque", "defaultdict", "OrderedDict", "Counter"}


def is_collection_literal(value: ast.AST | None) -> bool:
    if isinstance(value, ast.List | ast.Dict | ast.Set):
        return True
    return isinstance(value, ast.Call) and _name(value.func).split(".")[-1] in COLLECTION_FACTORIES


def _is_whole_object(scope: Scope, hit: ast.AST) -> bool:
    if isinstance(hit, ast.Attribute):
        return hit.attr == "__dict__"
    if isinstance(hit, ast.Call):
        return _name(hit.func).split(".")[-1] in SERIALIZERS
    return isinstance(hit, ast.Name) and scope.is_student(hit)


def _module_info(tree: ast.Module) -> tuple[set[str], set[str]]:
    """(names imported from outbound modules, module-level collection names)."""
    outbound, collections = set(), set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in OUTBOUND_MODULES:
            outbound.update(a.asname or a.name for a in node.names)
        if isinstance(node, ast.Import):
            outbound.update(a.asname or a.name for a in node.names if a.name.split(".")[0] in OUTBOUND_MODULES)
        if isinstance(node, ast.Assign | ast.AnnAssign) and is_collection_literal(node.value):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            collections.update(t.id for t in targets if isinstance(t, ast.Name))
    return outbound, collections


def _functions(tree: ast.AST):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]


def _parse_service_modules(ctx: DiffContext) -> dict[str, ast.Module]:
    """Every service module of the analyzed tree (summaries need unchanged helpers too)."""
    modules = {}
    paths = set(ctx.files())
    if ctx.mode != "staged":
        paths |= {p.relative_to(ctx.repo).as_posix() for p in ctx.repo.rglob("*.py")}
    for path in sorted(paths):
        if not is_service_python(path):
            continue
        source = ctx.read(path)
        if source is None:
            continue
        try:
            modules[path] = ast.parse(source)
        except SyntaxError:
            continue  # ruff reports syntax errors
    return modules


def build_summaries(modules: dict[str, ast.Module], fields: frozenset[str]) -> Summaries:
    outbound, collections = set(), set()
    for tree in modules.values():
        o, c = _module_info(tree)
        outbound |= o
        collections |= c
    summaries = Summaries(set(), set(), outbound, collections)
    for _ in range(3):
        for tree in modules.values():
            for func in _functions(tree):
                scope = Scope(fields, summaries, func)
                for node in _own_nodes(func.body):
                    if isinstance(node, ast.Return) and node.value is not None:
                        if scope.is_student(node.value):
                            summaries.student_funcs.add(func.name)
                        elif scope.exposure(node.value) is not None:
                            summaries.pii_funcs.add(func.name)
    return summaries


def check(ctx: DiffContext) -> list[Finding]:
    fields = pii_fields(ctx.read("app/privacy.py"))
    modules = _parse_service_modules(ctx)
    summaries = build_summaries(modules, fields)
    findings: list[Finding] = []
    changed_files = set(ctx.files())
    for path, tree in modules.items():
        if path not in changed_files:
            continue
        scopes = [(Scope(fields, summaries, func), _is_route(func)) for func in _functions(tree)]
        top_level = [s for s in tree.body if not isinstance(s, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)]
        scopes.append((Scope(fields, summaries, body=top_level), False))
        for scope, is_route in scopes:
            for kind, sink, exprs in scope.sinks(is_route):
                hit = next((h for e in exprs if (h := scope.exposure(e)) is not None), None)
                if hit is None:
                    continue
                if not (ctx.is_changed(path, sink.lineno, sink.end_lineno) or ctx.is_changed(path, hit.lineno)):
                    continue
                rule, severity, where, suggestion = SINK_RULES[kind]
                whole_object = _is_whole_object(scope, hit)
                what = ast.unparse(hit)[:80]
                findings.append(
                    Finding(
                        rule=rule,
                        severity=severity,
                        source="deterministic:pii_flow",
                        check="P3" if whole_object else "P2",
                        file=path,
                        line=hit.lineno,
                        message=f"Personal data (`{what}`) reaches {where} in plain text.",
                        suggestion=suggestion,
                    )
                )
    return findings


def outbound_signals(ctx: DiffContext) -> list[Signal]:
    """A5: new outbound channels on changed lines, for the AI to judge (AGENTS#2)."""
    signals = []
    for path in ctx.files():
        if not is_service_python(path):
            continue
        try:
            tree = ast.parse(ctx.read(path) or "")
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            line = getattr(node, "lineno", None)
            if line is None or not ctx.is_changed(path, line):
                continue
            detail = None
            if isinstance(node, ast.Import | ast.ImportFrom):
                modules = [node.module or ""] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names]
                hits = [m for m in modules if m.split(".")[0] in OUTBOUND_MODULES]
                detail = f"imports {', '.join(hits)}" if hits else None
            elif isinstance(node, ast.Call):
                name = _name(node.func)
                last = name.split(".")[-1]
                if name.split(".")[0] in OUTBOUND_MODULES or last in OUTBOUND_METHODS or last in LOG_HANDLERS:
                    detail = f"calls {name}()"
                elif last == "open" and any(
                    isinstance(a, ast.Constant) and str(a.value)[:1] in "wax" for a in node.args[1:2]
                ):
                    detail = "opens a file for writing"
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                tokens = set(node.name.lower().split("_"))
                hits = tokens & {
                    "send",
                    "notify",
                    "notification",
                    "export",
                    "upload",
                    "sync",
                    "webhook",
                    "track",
                    "email",
                    "sms",
                    "remind",
                    "reminder",
                }
                detail = f"defines {node.name}() (possible outbound: {', '.join(sorted(hits))})" if hits else None
            if detail:
                signals.append(Signal("A5", path, line, detail))
    return signals
