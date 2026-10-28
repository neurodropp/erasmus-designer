#!/usr/bin/env python3
"""Dependency-free validator for the explicit project-model JSON Schema subset.

This is not a general JSON Schema implementation. Unsupported keywords, formats,
remote references and recursive reference graphs are errors, never ignored.
The subset implements every keyword in config/project-model.schema.json.
"""
from datetime import date
import math
import re

KEYWORDS=frozenset({'$schema','$defs','$ref','title','description','type','required','properties','additionalProperties','items','oneOf','const','enum','format','uniqueItems','minimum','minLength','minItems','minProperties','pattern'})
TYPES=frozenset({'object','array','string','integer','number','boolean','null'})
DIALECT='https://json-schema.org/draft/2020-12/schema'


def _pointer(parts):
    return ''.join('/'+str(part).replace('~','~0').replace('/','~1') for part in parts)


def _number(value):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and (not isinstance(value,float) or math.isfinite(value))


def _type(value,kind):
    if kind=='null': return value is None
    if kind=='boolean': return isinstance(value,bool)
    if kind=='object': return isinstance(value,dict)
    if kind=='array': return isinstance(value,list)
    if kind=='string': return isinstance(value,str)
    if kind=='number': return _number(value)
    if kind=='integer': return _number(value) and (isinstance(value,int) or value.is_integer())
    return False


def _equal(a,b):
    """JSON value equality: booleans are distinct from numeric 0/1."""
    if _number(a) and _number(b): return a==b
    if type(a) is not type(b): return False
    if isinstance(a,list): return len(a)==len(b) and all(_equal(x,y) for x,y in zip(a,b))
    if isinstance(a,dict): return set(a)==set(b) and all(_equal(a[key],b[key]) for key in a)
    return a==b


def _ref(root,value):
    if not isinstance(value,str) or not value.startswith('#/'):
        raise ValueError('Only local nonrecursive #/ JSON Pointer references are supported')
    current=root
    for token in value[2:].split('/'):
        if re.search(r'~(?![01])',token): raise ValueError('Invalid reference escape')
        token=token.replace('~1','/').replace('~0','~')
        if not isinstance(current,dict) or token not in current: raise ValueError('Unresolved local reference '+value)
        current=current[token]
    if not isinstance(current,(dict,bool)): raise ValueError('Reference does not resolve to a schema')
    return current


def validate_schema(schema):
    """Inspect all schema nodes, including unused definitions, fail closed."""
    issues=[]; completed=set(); active=set()
    def issue(path,keyword,message):issues.append({'code':'unsupported-or-invalid-model-schema','schema_path':_pointer(path),'keyword':keyword,'message':message})
    def walk(node,path):
        if isinstance(node,bool):return
        if not isinstance(node,dict):issue(path,None,'Schema must be an object or boolean');return
        ident=id(node)
        if ident in active:issue(path,'$ref','Recursive schema reference is unsupported');return
        if ident in completed:return
        active.add(ident)
        for keyword in node:
            if keyword not in KEYWORDS:issue(path+(keyword,),keyword,'Unsupported keyword; extend validator before changing schema')
        if '$schema' in node and node['$schema']!=DIALECT:issue(path+('$schema',),'$schema','Unsupported schema dialect')
        for key in ('title','description'):
            if key in node and not isinstance(node[key],str):issue(path+(key,),key,'Annotation must be a string')
        if 'type' in node:
            types=node['type'];types=[types] if isinstance(types,str) else types
            if not isinstance(types,list) or not types or any(not isinstance(t,str) or t not in TYPES for t in types) or len(types)!=len(set(t for t in types if isinstance(t,str))):issue(path+('type',),'type','Invalid type declaration')
        if 'required' in node:
            value=node['required']
            if not isinstance(value,list) or any(not isinstance(k,str) for k in value) or len(value)!=len(set(k for k in value if isinstance(k,str))):issue(path+('required',),'required','Required must contain unique string keys')
        for key in ('properties','$defs'):
            if key in node:
                if not isinstance(node[key],dict):issue(path+(key,),key,'Schema map must be an object')
                else:
                    for name,child in node[key].items():
                        if not isinstance(name,str):issue(path+(key,),key,'Schema-map keys must be strings')
                        walk(child,path+(key,name))
        for key in ('additionalProperties','items'):
            if key in node:walk(node[key],path+(key,))
        if 'oneOf' in node:
            value=node['oneOf']
            if not isinstance(value,list) or not value:issue(path+('oneOf',),'oneOf','oneOf must be a nonempty array of schemas')
            else:
                for i,child in enumerate(value):walk(child,path+('oneOf',i))
        if 'enum' in node and (not isinstance(node['enum'],list) or not node['enum']):issue(path+('enum',),'enum','Enum must be a nonempty array')
        if 'uniqueItems' in node and not isinstance(node['uniqueItems'],bool):issue(path+('uniqueItems',),'uniqueItems','uniqueItems must be boolean')
        if 'minimum' in node and not _number(node['minimum']):issue(path+('minimum',),'minimum','minimum must be a finite number')
        for key in ('minLength','minItems','minProperties'):
            value=node.get(key)
            if key in node and (isinstance(value,bool) or not isinstance(value,int) or value<0):issue(path+(key,),key,'Bound must be a nonnegative integer')
        if 'format' in node and node['format']!='date':issue(path+('format',),'format','Only date format is supported and asserted')
        if 'pattern' in node:
            try:
                if not isinstance(node['pattern'],str):raise ValueError('Pattern must be a string')
                re.compile(node['pattern'],re.ASCII)
            except (ValueError,re.error) as exc:issue(path+('pattern',),'pattern',str(exc))
        if '$ref' in node:
            try:target=_ref(schema,node['$ref']);walk(target,path+('$ref',))
            except ValueError as exc:issue(path+('$ref',),'$ref',str(exc))
        active.remove(ident);completed.add(ident)
    walk(schema,())
    return {'passed':not issues,'issues':issues,'supported_keywords':sorted(KEYWORDS)}


def validate_instance(instance,schema):
    """Apply a fully inspected schema to a JSON instance, without mutation."""
    inspected=validate_schema(schema)
    if not inspected['passed']:return inspected
    issues=[]
    def flag(path,sp,keyword,message):issues.append({'code':'model-schema-violation','path':_pointer(path),'schema_path':_pointer(sp+(keyword,)),'keyword':keyword,'message':message})
    def walk(value,node,path,sp):
        if node is True:return
        if node is False:flag(path,sp,'boolean-schema','False schema forbids this value');return
        if '$ref' in node:walk(value,_ref(schema,node['$ref']),path,tuple(token.replace('~1','/').replace('~0','~') for token in node['$ref'][2:].split('/')))
        if 'type' in node:
            types=node['type'];types=[types] if isinstance(types,str) else types
            if not any(_type(value,kind) for kind in types):flag(path,sp,'type','Expected '+str(types));return
        if 'const' in node and not _equal(value,node['const']):flag(path,sp,'const','Value differs from required constant')
        if 'enum' in node and not any(_equal(value,item) for item in node['enum']):flag(path,sp,'enum','Value is not in enum')
        if 'oneOf' in node:
            count=0
            for i,child in enumerate(node['oneOf']):
                previous=len(issues);walk(value,child,path,sp+('oneOf',i))
                if len(issues)==previous:count+=1
                del issues[previous:]
            if count!=1:flag(path,sp,'oneOf','Expected exactly one matching branch; matched '+str(count))
        if _number(value) and 'minimum' in node and value<node['minimum']:flag(path,sp,'minimum','Value is below minimum')
        if isinstance(value,str):
            if 'minLength' in node and len(value)<node['minLength']:flag(path,sp,'minLength','String is shorter than minimum')
            if 'pattern' in node and re.search(node['pattern'],value,re.ASCII) is None:flag(path,sp,'pattern','String does not match pattern')
            if 'format' in node:
                try:
                    if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value) is None or date.fromisoformat(value).isoformat()!=value:raise ValueError('Invalid date')
                except ValueError:flag(path,sp,'format','Expected a real ISO calendar date YYYY-MM-DD')
        if isinstance(value,list):
            if 'minItems' in node and len(value)<node['minItems']:flag(path,sp,'minItems','Array is shorter than minimum')
            if node.get('uniqueItems') and any(_equal(item,prior) for i,item in enumerate(value) for prior in value[:i]):flag(path,sp,'uniqueItems','Array items are not unique')
            if 'items' in node:
                for i,item in enumerate(value):walk(item,node['items'],path+(i,),sp+('items',))
        if isinstance(value,dict):
            if 'minProperties' in node and len(value)<node['minProperties']:flag(path,sp,'minProperties','Object has fewer than minimum properties')
            for key in node.get('required',[]):
                if key not in value:flag(path+(key,),sp,'required','Required property is missing')
            properties=node.get('properties',{})
            for key,item in value.items():
                if not isinstance(key,str):flag(path,sp,'properties','JSON object key must be a string');continue
                if key in properties:walk(item,properties[key],path+(key,),sp+('properties',key))
                elif 'additionalProperties' in node:walk(item,node['additionalProperties'],path+(key,),sp+('additionalProperties',))
    def json_domain(value,path):
        if value is None or isinstance(value,(str,bool,int)):return
        if isinstance(value,float):
            if not math.isfinite(value):flag(path,(),'json-value','Nonfinite number is not a JSON value')
        elif isinstance(value,list):
            for i,item in enumerate(value):json_domain(item,path+(i,))
        elif isinstance(value,dict):
            for key,item in value.items():
                if not isinstance(key,str):flag(path,(),'json-value','JSON object keys must be strings')
                json_domain(item,path+(str(key),))
        else:flag(path,(),'json-value','Unsupported Python value is not a JSON value')
    json_domain(instance,())
    walk(instance,schema,(),())
    return {'passed':not issues,'issues':issues,'supported_keywords':sorted(KEYWORDS)}
