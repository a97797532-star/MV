# 한글 안내: 기존 제품 그룹 기준 데이터 분할을 처리하며 시점 간 Split 누수를 방지합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Portable adapter for existing Windows project splits; no relabeling of NG/masks."""
from pathlib import Path
import pandas as pd
from .legacy_bridge import core as preserved_core


# apply_preserved_split: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: df, manifest, root.
def apply_preserved_split(df,manifest,root):
    prior=pd.read_csv(manifest,keep_default_na=False)
    path_column='relative_path' if 'relative_path' in prior else 'image_path'
    split_column='project_split' if 'project_split' in prior else 'split'
    if path_column not in prior or split_column not in prior:raise ValueError('Split CSV requires relative_path/image_path and project_split/split')
    resolver=preserved_core().resolve_path
    normalized=[]
    for row in prior.to_dict('records'):
        path=str(row[path_column]).replace('\\','/')
        category=str(row.get('category',path.split('/')[0]))
        normalized.append(resolver(root,category,path))
    prior=prior.assign(_path=normalized)
    if prior._path.duplicated().any():raise ValueError('Duplicate image paths in preserved split CSV')
    allowed={'train':'train','val':'validation','validation':'validation','test':'test'}
    values=prior[split_column].astype(str).str.lower().map(allowed)
    if values.isna().any():raise ValueError('Unknown split label in preserved manifest')
    assignments=dict(zip(prior._path,values));original=dict(zip(prior._path,prior[split_column]))
    result=df.copy();result['analysis_hash_split']=result.split
    result['windows_project_split']=result.image_path.map(original).fillna('')
    result['split_origin']=result.image_path.map(lambda p:'preserved_manifest' if p in assignments else 'new_image_hash_split')
    result['split']=result.image_path.map(assignments).fillna(result.split)
    result['conservative_serial_id']=result.product_id
    # The original grouping is the category/status/defect/serial folder; all five views stay together.
    keys=dict(zip(prior._path,prior['product_key'])) if 'product_key' in prior else {}
    result['product_id']=[str(keys.get(p,Path(p).parent.as_posix())) if p in assignments else pid for p,pid in zip(result.image_path,result.product_id)]
    if (result.groupby('product_id').split.nunique()>1).any():raise ValueError('Preserved product key crosses splits')
    return result,dict(manifest_rows=len(prior),matched=int(result.image_path.isin(assignments).sum()),new_images=int((result.split_origin=='new_image_hash_split').sum()),conservative_serial_cross_split_groups=int((result.groupby('conservative_serial_id').split.nunique()>1).sum()),identity_note='Serial numbers reused across quality/defect groups; conservative alias crossings are not proof of physical identity')


# reproduce_windows_project_split: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: df.
def reproduce_windows_project_split(df):
    """Original executed notebook cell 28: folder key + two seed-42 train_test_split calls."""
    from sklearn.model_selection import train_test_split
    from .legacy_bridge import notebook_function
    extract=notebook_function('extract_product_info')
    result=df.copy();result['conservative_serial_id']=result.product_id if 'product_id' in result else ''
    keys=[]
    for row in result.to_dict('records'):
        quality,defect,serial=extract(row['image_path'])
        if serial=='UNKNOWN':raise ValueError('Unrecognized original product folder')
        keys.append('/'.join([row['category'],quality,defect,serial]))
    result['windows_product_key']=keys
    products=result[['windows_product_key']].drop_duplicates()
    if len(products)<4:raise ValueError('Need at least four complete product groups for legacy 70/15/15 split')
    train,temp=train_test_split(products,test_size=.30,random_state=42,shuffle=True)
    val,test=train_test_split(temp,test_size=.50,random_state=42,shuffle=True)
    assignment={key:label for table,label in [(train,'train'),(val,'val'),(test,'test')] for key in table.windows_product_key}
    if 'split' in result:result['analysis_hash_split']=result.split
    result['windows_project_split']=result.windows_product_key.map(assignment)
    result['split']=result.windows_project_split.replace({'val':'validation'})
    result['product_id']=result.windows_product_key
    result['split_origin']='windows-executed-notebook-cell28-seed42'
    return result
