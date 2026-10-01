"""Assemble ../index.html from page_src.html + d3.v7.min.js + ../data/ucsd_local_data.json"""
s=open('page_src.html',encoding='utf-8').read()
s=s.replace('/*__D3__*/',open('d3.v7.min.js',encoding='utf-8').read(),1)
s=s.replace('/*__DATA__*/',open('../data/ucsd_local_data.json',encoding='utf-8').read().replace('</','<\\/'),1)
open('../index.html','w',encoding='utf-8').write(s); print(len(s))
