"""Refresh workbook source cells from analysis.json, preserving formulas and native pivots.
The companion workbook uses fixed template dimensions; changed record counts require
extending the workbook's source tables/formula bounds deliberately rather than truncation.
"""
import json, posixpath, zipfile
from pathlib import Path
import xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parent
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
def tag(x):return '{'+NS+'}'+x
E.register_namespace('',NS)
def refresh():
    p=ROOT/'workbooks/model.xlsx';d=json.loads((ROOT/'outputs/analysis.json').read_text(encoding='utf-8'))
    with zipfile.ZipFile(p) as z:parts={n:z.read(n) for n in z.namelist()}
    book=E.fromstring(parts['xl/workbook.xml']);rels=E.fromstring(parts['xl/_rels/workbook.xml.rels'])
    targets={x.attrib['Id']:posixpath.normpath('xl/'+x.attrib['Target']).lstrip('/') if not x.attrib['Target'].startswith('/') else x.attrib['Target'].lstrip('/') for x in rels}
    paths={x.attrib['name']:targets[x.attrib['{'+REL+'}id']] for x in book.find(tag('sheets'))}
    updates={}
    if 'commerce-close-lab'=='retail-finance-lab':
        if len(d['actuals'])!=18 or len(d['segment_actuals'])!=162 or len(d['budget'])!=162:raise ValueError('Template requires 18 months and 162 segments; extend the model before refreshing another shape')
        updates['Actuals']={(5+i,3):[x['month'],x['units'],x['revenue'],x['variable_cost'],x['merchandise_cost'],x['fixed_cost'],x['ebitda']] for i,x in enumerate(d['actuals'])}
        updates['Summary']={(22+i,3):[x['month'],x['revenue'],x['ebitda']] for i,x in enumerate(d['actuals'])}
        updates['Summary'][(12,4)]=[d['backtest']['seasonal_wape']]
        updates['Summary'][(13,4)]=[d['backtest']['trailing_mean_wape']]
        updates['Summary'][(14,4)]=[d['orders']]
        updates['Segments']={(5+i,3):[x['month'],x['region'],x['category'],x['units'],x['revenue'],x['variable_cost'],x['merchandise_cost'],x['fixed_cost'],x['revenue']-x['variable_cost']-x['fixed_cost']] for i,x in enumerate(d['segment_actuals'])}
        amap={(x['month'],x['region'],x['category']):x for x in d['segment_actuals']}
        updates['Variance bridge']={}
        for i,b in enumerate(d['budget']):
            a=amap[(b['month'],b['region'],b['category'])]
            updates['Variance bridge'][(15+i,3)]=[f"{b['month']} {b['region']} {b['category']}",b['units'],b['net_price'],b['variable_cost'],a['units'],a['revenue']/a['units'],a['variable_cost']/a['units'],b['fixed_cost'],a['fixed_cost']]
    else:
        if len(d['journals'])!=4183 or len(d['exceptions'])!=11:raise ValueError('Template record count changed; extend Excel source ranges, trial balance SUMIFS and PivotTable bounds before refresh')
        updates['Journals']={}
        for i,x in enumerate(d['journals']):
            updates['Journals'][(5+i,3)]=[x['journal_id'],x['date'],x['account']]
            updates['Journals'][(5+i,7)]=[x['debit_cents']/100,x['credit_cents']/100]
        updates['Exceptions']={(5+i,3):[x['rule'],x['source_id'],x['amount_cents']/100,x['detail'],x['severity'],x['owner'],x['status']] for i,x in enumerate(d['exceptions'])}
        keys=list(d['checks'])
        updates['Checks']={(6+i,4):[d['checks'][k]/100] for i,k in enumerate(keys[1:])}
    def col(n):
        s=''
        while n:n,j=divmod(n-1,26);s=chr(65+j)+s
        return s
    for name,blocks in updates.items():
        tree=E.fromstring(parts[paths[name]]);cells={x.attrib['r']:x for x in tree.iter(tag('c'))}
        data=tree.find(tag('sheetData'));rows={int(x.attrib['r']):x for x in data}
        for (rn,cn),values in blocks.items():
            for j,value in enumerate(values):
                ref=col(cn+j)+str(rn);cell=cells.get(ref)
                if cell is None:
                    row=rows.get(rn)
                    if row is None:row=E.SubElement(data,tag('row'),r=str(rn));rows[rn]=row
                    cell=E.SubElement(row,tag('c'),r=ref);cells[ref]=cell
                if cell.find(tag('f')) is not None:raise ValueError('Source update would overwrite formula '+name+'!'+ref)
                for x in list(cell):cell.remove(x)
                if isinstance(value,str):
                    cell.set('t','inlineStr');E.SubElement(E.SubElement(cell,tag('is')),tag('t')).text=value
                else:
                    cell.attrib.pop('t',None);E.SubElement(cell,tag('v')).text=str(value)
        parts[paths[name]]=E.tostring(tree,encoding='utf-8',xml_declaration=True)
    calc=book.find(tag('calcPr'))
    if calc is None:calc=E.SubElement(book,tag('calcPr'))
    calc.set('fullCalcOnLoad','1');calc.set('forceFullCalc','1');calc.set('calcMode','auto')
    parts['xl/workbook.xml']=E.tostring(book,encoding='utf-8',xml_declaration=True)
    for n,b in list(parts.items()):
        if n.startswith('xl/pivotCache/pivotCacheDefinition') and n.endswith('.xml'):
            t=E.fromstring(b);t.set('refreshOnLoad','1');parts[n]=E.tostring(t,encoding='utf-8',xml_declaration=True)
    tmp=p.with_suffix('.new.xlsx')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in parts.items():z.writestr(n,b)
    tmp.replace(p)
    print('Updated workbook inputs. Open in Excel, Refresh All, recalculate and save; previous cached output values are stale until then.')
if __name__=='__main__':refresh()
