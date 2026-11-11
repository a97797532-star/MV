"""무결성·경계·누수·마스크 미제공 의미를 검사하는 작은 계약 테스트."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from core import components, laplacian, nearest, build_manifest, audit, project_split
from make_demo import generate


class ArrayContracts(unittest.TestCase):
    def test_empty(self):
        labels,regions=components(np.zeros((5,7),bool))
        self.assertEqual(len(regions),0);self.assertEqual(labels.sum(),0)

    def test_diagonal_and_border(self):
        a=np.zeros((5,7),bool);a[0,0]=a[1,1]=True;a[4,6]=True
        labels,regions=components(a)
        regions=sorted((r for _,r in regions),key=lambda r:r['x0'])
        self.assertEqual(len(regions),2)
        self.assertEqual(regions[0],dict(area=2,x0=0,y0=0,x1=2,y1=2,cx=.5,cy=.5))
        self.assertEqual(regions[1],dict(area=1,x0=6,y0=4,x1=7,y1=5,cx=6.,cy=4.))

    def test_laplacian_boundary_oracle(self):
        a=np.arange(35,dtype=float).reshape(5,7)**2
        p=np.pad(a,1,mode='reflect')
        expected=p[:-2,1:-1]+p[2:,1:-1]+p[1:-1,:-2]+p[1:-1,2:]-4*a
        np.testing.assert_allclose(laplacian(a),expected,atol=1e-10)

    def test_resize_pixel_mapping(self):
        a=np.arange(16).reshape(4,4)
        np.testing.assert_array_equal(nearest(a,2),a[np.ix_([1,3],[1,3])])
        np.testing.assert_array_equal(nearest(a,4),a)
        m=np.zeros((4,4),int);m[0,0]=1
        self.assertEqual(nearest(m,2).sum(),0)

    def test_constant_and_singleton(self):
        np.testing.assert_array_equal(laplacian(np.ones((1,4))),np.zeros((1,4)))


class DataContracts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.dest=Path(self.tmp.name)
        self.demo=generate(self.dest/'demo', image_size=(64,80))
        self.manifest=build_manifest(self.demo/'images',self.demo/'jsons',self.dest/'work')
    def tearDown(self):self.tmp.cleanup()

    def test_missing_mask_is_unknown(self):
        m,i=audit(self.demo/'images',self.manifest,self.dest/'audit')
        self.assertEqual(len(i),0)
        self.assertEqual((m.mask_state=='not_provided').sum(),2)
        self.assertTrue((m[m.mask_state=='not_provided'].anomaly_class=='HS').all())

    def test_corrupt_image_and_bad_mask(self):
        m=self.manifest.copy();p=self.demo/'images'/m.iloc[0].image_path;p.write_bytes(b'bad image')
        p=self.demo/'images'/m.iloc[1].mask_path;Image.fromarray(np.ones((3,3),np.uint8)).save(p)
        checked,issues=audit(self.demo/'images',m,self.dest/'bad')
        self.assertIn('image_error',set(issues.issue));self.assertIn('mask_error',set(issues.issue))
        self.assertIn('error',set(checked.mask_state))

    def test_group_split_holdout(self):
        m=project_split(self.manifest,42,['ZW'])
        self.assertTrue((m.groupby(['category','sample_key']).project_split.nunique()==1).all())
        self.assertTrue((m[m.anomaly_class=='ZW'].project_split=='test').all())
        self.assertTrue(m.official_split.equals(self.manifest.official_split))
        self.assertTrue(project_split(self.manifest,42,['ZW']).equals(m))

    def test_duplicate_key_and_cross_split_hash(self):
        m=self.manifest.copy();source=m.iloc[0]
        m.loc[m.index[-1],'image_path']=source.image_path
        m=__import__('pandas').concat([m,m.iloc[[0]]],ignore_index=True)
        _,issues=audit(self.demo/'images',m,self.dest/'bad')
        self.assertIn('duplicate_key',set(issues.issue));self.assertIn('hash_split_leak',set(issues.issue))


if __name__=='__main__':unittest.main()
