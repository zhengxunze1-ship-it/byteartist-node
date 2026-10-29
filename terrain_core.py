"""Deterministic Terrain Tile Studio 0.1.0 algorithms, specification v1.0.
Arrays use HWC sRGB floats in [0, 1]. Scalar maps use HW floats.
All spatial filtering and gradients wrap in both axes.
"""
import math
import numpy as np

MAP_NAMES = ('BaseColor','Height','Normal','Roughness','Metallic','AO','ORM')

def prepare_seam(image, band_ratio=0.05):
    image = np.asarray(image)
    if image.ndim != 3 or image.shape[2] not in (3,4):
        raise ValueError('Expected an RGB or RGBA image')
    if not .01 <= band_ratio <= .30:
        raise ValueError('band_ratio must be within 0.01–0.30')
    h,w,_ = image.shape
    # The document defines output(x,y)=input(x+floor(w/2),y+floor(h/2)).
    shifted = np.roll(image,(-h//2 if h%2==0 else -(h//2),-(w//2)),axis=(0,1))
    bx=max(1,math.floor(w*band_ratio+.5)); by=max(1,math.floor(h*band_ratio+.5))
    yy,xx = np.ogrid[:h,:w]
    mask=((abs(xx-w//2)<=bx)|(abs(yy-h//2)<=by))
    guide=shifted.copy()
    guide[mask]=[1,0,0,1] if image.shape[2]==4 else [1,0,0]
    return shifted, guide, mask.astype(np.float32)

def wrap_box_blur(image,radius):
    image=np.asarray(image,dtype=np.float64)
    result=image
    k=2*radius+1
    for axis in (0,1):
        padding=[(0,0)]*result.ndim
        padding[axis]=(radius,radius)
        extended=np.pad(result,padding,mode='wrap')
        cumulative=np.cumsum(extended,axis=axis,dtype=np.float64)
        shape=list(cumulative.shape);shape[axis]=1
        cumulative=np.concatenate((np.zeros(shape),cumulative),axis=axis)
        upper=[slice(None)]*result.ndim; lower=upper.copy()
        upper[axis]=slice(k,None); lower[axis]=slice(None,-k)
        result=(cumulative[tuple(upper)]-cumulative[tuple(lower)])/k
    return result

def linear_luminance(image):
    rgb=np.asarray(image,dtype=np.float64)[...,:3]
    linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    return linear @ np.array([.2126,.7152,.0722])

def normal_from_height(height,strength=4.0,normal_format='OpenGL'):
    def sample(dx,dy): return np.roll(height,(-dy,-dx),axis=(0,1))
    dx=sample(1,-1)+2*sample(1,0)+sample(1,1)-sample(-1,-1)-2*sample(-1,0)-sample(-1,1)
    dy=sample(-1,1)+2*sample(0,1)+sample(1,1)-sample(-1,-1)-2*sample(0,-1)-sample(1,-1)
    n=np.stack((-dx*strength,-dy*strength,np.ones_like(height)),axis=-1)
    n/=np.linalg.norm(n,axis=-1,keepdims=True)
    if normal_format=='DirectX': n[...,1]*=-1
    elif normal_format!='OpenGL': raise ValueError('Unknown normal format')
    return np.clip(n*.5+.5,0,1)

def pbr_from_basecolor(image,normal_strength=4.0,height_contrast=1.15,ao_strength=1.25,
                       roughness_base=.68,roughness_variation=.28,metallic=0.0,
                       invert_height=False,normal_format='OpenGL'):
    rgb=np.clip(np.asarray(image,dtype=np.float64)[...,:3],0,1)
    h,w,_=rgb.shape
    luminance=linear_luminance(rgb)
    low=wrap_box_blur(luminance,max(2,math.floor(min(w,h)*.008+.5)))
    ao_frequency=wrap_box_blur(luminance,max(6,math.floor(min(w,h)*.035+.5)))
    height=low+(luminance-low)*.45
    if invert_height: height=1-height
    height=(height-.5)*height_contrast+.5
    height=np.clip((height-height.min())/max(.0001,float(height.max()-height.min())),0,1)
    normal=normal_from_height(height,normal_strength,normal_format)
    difference=np.minimum(1,np.abs(luminance-low)*8)
    highlight=np.maximum(0,luminance-.72)*.35
    roughness=np.clip(roughness_base+(difference-.35)*roughness_variation-highlight,.04,1)
    metal=np.full((h,w),np.clip(metallic,0,1),dtype=np.float64)
    ao=np.clip(1-np.maximum(0,ao_frequency-luminance)*ao_strength*5,0,1)
    orm=np.stack((ao,roughness,metal),axis=-1)
    return dict(zip(MAP_NAMES,(rgb,height,normal,roughness,metal,ao,orm)))
