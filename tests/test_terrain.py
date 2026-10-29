import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import terrain_core as tc

class TerrainTests(unittest.TestCase):
    def test_offset_even_roundtrip(self):
        a=np.arange(8*10*3).reshape(8,10,3)/240
        shifted,guide,mask=tc.prepare_seam(a,.05)
        np.testing.assert_array_equal(shifted[0,0],a[4,5])
        np.testing.assert_array_equal(tc.prepare_seam(shifted,.05)[0],a)

    def test_offset_odd_direction_and_dimensions(self):
        a=np.arange(5*7*3).reshape(5,7,3)/105
        shifted,_,_=tc.prepare_seam(a,.05)
        self.assertEqual(shifted.shape,a.shape)
        np.testing.assert_array_equal(shifted[0,0],a[2,3])
        np.testing.assert_array_equal(shifted[4,6],a[1,2])

    def test_mask_1024_boundaries_and_guide(self):
        a=np.full((1024,1024,3),.25)
        shifted,guide,mask=tc.prepare_seam(a,.05)
        self.assertEqual(mask[0,460],0)
        self.assertEqual(mask[0,461],1)
        self.assertEqual(mask[0,563],1)
        self.assertEqual(mask[0,564],0)
        self.assertEqual(int(mask.sum()),1024*103*2-103*103)
        np.testing.assert_array_equal(guide[mask==0],shifted[mask==0])
        self.assertTrue(np.all(guide[mask==1]==[1,0,0]))

    def test_wrap_blur_impulse_and_constant(self):
        a=np.zeros((9,11)); a[0,0]=1
        result=tc.wrap_box_blur(a,1)
        self.assertAlmostEqual(result[-1,-1],1/9)
        self.assertAlmostEqual(result.sum(),1)
        np.testing.assert_allclose(tc.wrap_box_blur(np.full((3,4),.42),6),.42)

    def test_linear_luminance(self):
        a=np.array([[[0,0,0],[1,1,1],[1,0,0],[0,1,0],[0,0,1],[.04045]*3]])
        np.testing.assert_allclose(tc.linear_luminance(a),[[0,1,.2126,.7152,.0722,.04045/12.92]],atol=1e-8)

    def test_flat_material(self):
        maps=tc.pbr_from_basecolor(np.full((16,16,3),.5))
        np.testing.assert_allclose(maps['Height'],0,atol=1e-6)
        np.testing.assert_allclose(maps['Normal'],np.broadcast_to([.5,.5,1],(16,16,3)),atol=1e-6)
        np.testing.assert_allclose(maps['Roughness'],.582,atol=1e-6)
        np.testing.assert_allclose(maps['Metallic'],0)
        np.testing.assert_allclose(maps['AO'],1,atol=1e-6)

    def test_normal_direction_and_directx(self):
        h=np.tile(np.arange(8,dtype=float)/7,(8,1))
        gl=tc.normal_from_height(h,4,'OpenGL')
        self.assertLess(gl[3,3,0],.5)
        self.assertAlmostEqual(gl[3,3,1],.5)
        self.assertGreater(gl[3,0,0],.5)
        dx=tc.normal_from_height(h.T,4,'DirectX')
        gl=tc.normal_from_height(h.T,4,'OpenGL')
        np.testing.assert_allclose(gl[:,:,0],dx[:,:,0])
        np.testing.assert_allclose(gl[:,:,1]+dx[:,:,1],1)

    def test_pbr_wrap_equivariance_and_channel_packing(self):
        a=np.random.default_rng(7).random((24,32,3))
        p=tc.pbr_from_basecolor(a)
        q=tc.pbr_from_basecolor(np.roll(a,(7,5),(0,1)))
        self.assertEqual(list(p),['BaseColor','Height','Normal','Roughness','Metallic','AO','ORM'])
        for key in p:
            np.testing.assert_allclose(np.roll(p[key],(7,5),(0,1)),q[key],atol=2e-6)
            self.assertTrue(np.isfinite(p[key]).all())
            self.assertTrue(((p[key]>=0)&(p[key]<=1)).all())
        np.testing.assert_array_equal(p['ORM'][:,:,0],p['AO'])
        np.testing.assert_array_equal(p['ORM'][:,:,1],p['Roughness'])
        np.testing.assert_array_equal(p['ORM'][:,:,2],p['Metallic'])

    def test_invert_height(self):
        a=np.random.default_rng(3).random((16,20,3))
        x=tc.pbr_from_basecolor(a)
        y=tc.pbr_from_basecolor(a,invert_height=True)
        np.testing.assert_allclose(x['Height']+y['Height'],1,atol=1e-6)

if __name__=='__main__': unittest.main()
