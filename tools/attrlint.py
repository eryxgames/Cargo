"""List self.X reads that no method or assignment in the class defines (wrong-object bugs).

usage: attrlint.py cargo.py
"""
import ast,collections,sys
src=open(sys.argv[1]).read(); t=ast.parse(src)
classes={n.name:n for n in t.body if isinstance(n,ast.ClassDef)}
def info(c):
    d=set()
    for m in c.body:
        if isinstance(m,ast.FunctionDef): d.add(m.name)
        elif isinstance(m,ast.Assign):
            for tg in m.targets:
                if isinstance(tg,ast.Name): d.add(tg.id)
    for x in ast.walk(c):
        if isinstance(x,ast.Attribute) and isinstance(x.value,ast.Name) and x.value.id=='self' and isinstance(x.ctx,ast.Store): d.add(x.attr)
    for b in c.bases:
        if isinstance(b,ast.Name) and b.id in classes: d|=info(classes[b.id])
    return d
n=0
for c in classes.values():
    d=info(c); miss=collections.defaultdict(list)
    for x in ast.walk(c):
        if isinstance(x,ast.Attribute) and isinstance(x.value,ast.Name) and x.value.id=='self' and isinstance(x.ctx,ast.Load) and x.attr not in d:
            miss[x.attr].append(x.lineno)
    for k,v in sorted(miss.items()): print(f"{c.name}.{k}: lines {v[:6]}"); n+=1
print("broken self references:",n)
