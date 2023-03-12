import ast

from mattrs import apply_attrs, attrs_predicate

with open("t.py") as f:
    parsed_ast = ast.parse(f.read())


def walk_ast(mod: ast.Module) -> ast.Module:
    new_stmts = []
    for stmt in mod.body:
        match stmt:
            case ast.ClassDef():
                if attrs_predicate(stmt):
                    stmt = apply_attrs(stmt)
        new_stmts.append(stmt)
    mod.body = new_stmts
    return mod


print(ast.dump(parsed_ast))
walked = walk_ast(parsed_ast)
print(ast.dump(walked))
print(ast.unparse(walked))
