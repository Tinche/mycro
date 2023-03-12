"""Macro attrs."""
import ast
from ast import (
    AnnAssign,
    Assign,
    Attribute,
    Call,
    ClassDef,
    Compare,
    Constant,
    Eq,
    ExceptHandler,
    Expr,
    FormattedValue,
    FunctionDef,
    If,
    ImportFrom,
    In,
    IsNot,
    JoinedStr,
    Load,
    Name,
    Return,
    Set,
    Store,
    Subscript,
    Try,
    Tuple,
    UnaryOp,
    USub,
    alias,
    arg,
    arguments,
    keyword,
    stmt,
)
from types import NoneType
from typing import TypeAlias


def attrs_predicate(cls: ClassDef) -> bool:
    for dec in cls.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "define":
            return True
    return False


Attributes: TypeAlias = list[tuple[str, Name, Constant | None]]


def gather_attributes(cls: ClassDef) -> tuple[list[stmt], Attributes]:
    attributes = []
    new_body = []
    for stmt in cls.body:
        match stmt:
            case AnnAssign(target=t, annotation=a, value=val):
                if (
                    isinstance(t, Name)
                    and isinstance(a, ast.Name)
                    and isinstance(val, (Constant, NoneType))
                ):
                    attributes.append((t.id, a, val))
                    continue
        new_body.append(stmt)

    return new_body, attributes


def apply_attrs(cls: ClassDef) -> ClassDef:
    cls.decorator_list = [
        d
        for d in cls.decorator_list
        if not isinstance(d, ast.Name) or not d.id == "define"
    ]
    body, attributes = gather_attributes(cls)
    cls.body = make_attrs_tuple_stmts(cls.name, attributes)
    cls.body.append(body)
    init = make_init(attributes)
    eq = make_eq(attributes, cls.name)
    cls.body.append(make_slots(attributes))
    cls.body.append(make_match(attributes))
    cls.body.append(init)
    cls.body.append(eq)
    cls.body.extend(make_repr(attributes))
    return cls


def make_attrs_tuple_stmts(cls_name: str, attrs: Attributes) -> list[stmt]:
    return [
        ClassDef(
            f"{cls_name}Attributes",
            [
                Subscript(
                    Name("tuple"),
                    Tuple([Subscript(Name("GenericAttribute"), a[1]) for a in attrs]),
                )
            ],
            [],
            [
                FunctionDef(
                    a[0],
                    arguments([], [arg("self")], None, [], [], None, []),
                    [Return(Subscript(Name("self"), Constant(i)))],
                    [Name("property")],
                    Subscript(Name("GenericAttribute"), a[1]),
                    lineno=0,
                )
                for i, a in enumerate(attrs)
            ],
            [],
        ),
        Assign(
            [Name("__attrs_attrs__", ctx=Store())],
            Call(
                Name("TestAttributes"),
                [
                    Tuple(
                        [
                            Call(
                                Name("GenericAttribute"),
                                [
                                    Constant(a[0]),
                                    Name("NOTHING") if a[2] is None else a[2],
                                    Constant(None),
                                    Constant(True),
                                    Constant(None),
                                    Constant(None),
                                    Constant(True),
                                    Constant(False),
                                ],
                                keywords=[keyword("type", a[1])],
                            )
                            for a in attrs
                        ]
                    )
                ],
                keywords=[],
            ),
            lineno=0,
        ),
    ]


def make_slots(attributes: Attributes) -> Assign:
    return Assign(
        targets=[Name("__slots__", ctx=Store())],
        value=Tuple(elts=[Constant(value=an) for an, *_ in attributes], ctx=Load()),
        lineno=0,
    )


def make_match(attributes: Attributes) -> Assign:
    return Assign(
        targets=[Name("__match_args__", ctx=Store())],
        value=Tuple(elts=[Constant(value=an) for an, *_ in attributes], ctx=Load()),
        lineno=0,
    )


def make_init(attributes: Attributes) -> FunctionDef:
    args = [ast.arg("self")]
    body = []
    defaults = []
    for an, at, ad in attributes:
        args.append(arg(an, annotation=at))
        if ad is not None:
            defaults.append(ad)
        body.append(
            Assign(
                [Attribute(ast.Name("self", ast.Load()), an, ctx=Store())],
                Name(an, ctx=ast.Load()),
                lineno=0,
            )
        )
    return FunctionDef(
        "__init__",
        arguments(posonlyargs=[], args=args, kwonlyargs=[], defaults=defaults),
        body=body,
        returns=Constant(None),
        decorator_list=[],
        lineno=0,
    )


def make_eq(attributes: Attributes, cls_name: str) -> FunctionDef:
    args = [arg("self"), arg("other", annotation=Constant(cls_name))]
    body = [
        ast.If(
            test=Compare(
                left=Attribute(
                    value=Name(id="other", ctx=Load()),
                    attr="__class__",
                    ctx=Load(),
                ),
                ops=[IsNot()],
                comparators=[
                    Attribute(
                        value=Name(id="self", ctx=Load()),
                        attr="__class__",
                        ctx=Load(),
                    )
                ],
            ),
            body=[Return(value=Name(id="NotImplemented", ctx=Load()))],
            orelse=[],
        ),
        Return(
            value=Compare(
                left=Tuple(
                    elts=[
                        Attribute(
                            value=Name(id="self", ctx=Load()), attr=an, ctx=Load()
                        )
                        for an, *_ in attributes
                    ],
                    ctx=Load(),
                ),
                ops=[Eq()],
                comparators=[
                    Tuple(
                        elts=[
                            Attribute(
                                value=Name(id="other", ctx=Load()), attr=an, ctx=Load()
                            )
                            for an, *_ in attributes
                        ],
                        ctx=Load(),
                    )
                ],
            )
        ),
    ]
    return FunctionDef(
        "__eq__",
        arguments(posonlyargs=[], args=args, kwonlyargs=[], defaults=[]),
        body=body,
        returns=Name("bool"),
        decorator_list=[],
        lineno=0,
    )


def make_repr(attributes: Attributes) -> list[stmt]:
    exprs = []
    for ix, (an, *_) in enumerate(attributes):
        exprs.append(Constant(f"{'' if ix == 0 else ', '}{an}="))
        exprs.append(
            FormattedValue(
                Attribute(
                    value=Name(id="self", ctx=Load()),
                    attr=an,
                    ctx=Load(),
                ),
                conversion=114,
            ),
        )
    body = [
        Try(
            body=[
                Assign(
                    targets=[Name(id="already_repring", ctx=Store())],
                    value=Attribute(
                        Name("repr_context"),
                        attr="already_repring",
                        ctx=Load(),
                    ),
                    lineno=0,
                )
            ],
            handlers=[
                ExceptHandler(
                    type=Name(id="AttributeError", ctx=Load()),
                    body=[
                        Assign(
                            targets=[Name(id="already_repring", ctx=Store())],
                            value=Set(
                                elts=[
                                    Call(
                                        func=Name(id="id", ctx=Load()),
                                        args=[Name(id="self", ctx=Load())],
                                        keywords=[],
                                    )
                                ]
                            ),
                            lineno=0,
                        ),
                        Assign(
                            targets=[
                                Attribute(
                                    Name("repr_context"),
                                    attr="already_repring",
                                    ctx=Store(),
                                )
                            ],
                            value=Name(id="already_repring", ctx=Load()),
                            lineno=0,
                        ),
                    ],
                )
            ],
            orelse=[
                If(
                    test=Compare(
                        left=Call(
                            func=Name(id="id", ctx=Load()),
                            args=[Name(id="self", ctx=Load())],
                            keywords=[],
                        ),
                        ops=[In()],
                        comparators=[Name(id="already_repring", ctx=Load())],
                    ),
                    body=[Return(value=Constant(value="..."))],
                    orelse=[
                        Expr(
                            value=Call(
                                func=Attribute(
                                    value=Name(id="already_repring", ctx=Load()),
                                    attr="add",
                                    ctx=Load(),
                                ),
                                args=[
                                    Call(
                                        func=Name(id="id", ctx=Load()),
                                        args=[Name(id="self", ctx=Load())],
                                        keywords=[],
                                    )
                                ],
                                keywords=[],
                            )
                        )
                    ],
                )
            ],
            finalbody=[],
        ),
        Try(
            body=[
                Return(
                    value=JoinedStr(
                        values=[
                            FormattedValue(
                                value=Subscript(
                                    value=Call(
                                        func=Attribute(
                                            value=Attribute(
                                                value=Attribute(
                                                    value=Name(id="self", ctx=Load()),
                                                    attr="__class__",
                                                    ctx=Load(),
                                                ),
                                                attr="__qualname__",
                                                ctx=Load(),
                                            ),
                                            attr="rsplit",
                                            ctx=Load(),
                                        ),
                                        args=[Constant(value=">."), Constant(value=1)],
                                        keywords=[],
                                    ),
                                    slice=UnaryOp(op=USub(), operand=Constant(value=1)),
                                    ctx=Load(),
                                ),
                                conversion=-1,
                            ),
                            Constant("("),
                            *exprs,
                            Constant(")"),
                        ]
                    )
                )
            ],
            handlers=[],
            orelse=[],
            finalbody=[
                Expr(
                    value=Call(
                        func=Attribute(
                            value=Name(id="already_repring", ctx=Load()),
                            attr="remove",
                            ctx=Load(),
                        ),
                        args=[
                            Call(
                                func=Name(id="id", ctx=Load()),
                                args=[Name(id="self", ctx=Load())],
                                keywords=[],
                            )
                        ],
                        keywords=[],
                    )
                )
            ],
        ),
    ]
    return [
        ImportFrom("attr._compat", [alias("repr_context")]),
        FunctionDef(
            "__repr__",
            arguments(
                posonlyargs=[],
                args=[arg(arg="self"), arg(arg="repr_context")],
                kwonlyargs=[],
                defaults=[Name("repr_context")],
            ),
            body=body,
            returns=Name("str"),
            decorator_list=[],
            lineno=0,
        ),
    ]
