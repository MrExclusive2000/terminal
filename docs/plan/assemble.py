import re, os
D=os.path.dirname(os.path.abspath(__file__))
S=os.path.join(D,'src')+os.sep
OUT=os.path.join(D,'argus-build-plan-v2.html')
n1=open(S+'n1.html').read(); n3=open(S+'n3.html').read(); know=open(S+'n2_know.html').read()
n4=open(S+'n4.html').read(); n5=open(S+'n5.html').read(); n6=open(S+'n6.html').read()
n7=open(S+'n7.html').read(); figs=open(S+'figures.html').read()

assert n3.count('<!--MOCKUPS-->')==1
n3=n3.replace('<!--MOCKUPS-->', figs)
b=n3.index('<section id="brain">')
scrn,brain=n3[:b].rstrip(), n3[b:].rstrip()
for part in (scrn,brain):
    assert part.count('<section id=')==1 and part.count('</section>')==1

css="\n".join(open(f).read() for f in (os.path.join(D,x) for x in ('tokens.css','doc.css','ui.css')))
marker='display=swap">'
assert n1.count(marker)==1
n1=n1.replace(marker, marker+"\n<style>\n"+css+"\n</style>")

doc="\n\n".join(p.rstrip() for p in (n1,scrn,know,brain,n4,n5,n6,n7))+"\n"
open(OUT,'w').write(doc)
print("assembled:",len(doc),"bytes | sections:",re.findall(r'<section id="([a-z]+)"',doc))
