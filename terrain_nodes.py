"""ComfyUI adapter for the Terrain Tile Studio deterministic algorithms."""
import json
import os
import numpy as np
import torch
from PIL import Image
import folder_paths
from .terrain_core import prepare_seam, pbr_from_basecolor, MAP_NAMES


def tensor(array):
    return torch.from_numpy(np.ascontiguousarray(array,dtype=np.float32))


class TerrainPrepareSeam:
    CATEGORY = 'Terrain Tile Studio'
    FUNCTION = 'prepare'
    RETURN_TYPES = ('IMAGE','IMAGE','MASK')
    RETURN_NAMES = ('shifted_image','seam_guide','seam_mask')
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'image': ('IMAGE',), 'band_ratio': ('FLOAT', {'default': .05,'min':.01,'max':.30,'step':.01})}}
    def prepare(self,image,band_ratio):
        results=[prepare_seam(a,band_ratio) for a in image.detach().cpu().numpy()]
        return tuple(tensor(np.stack([r[i] for r in results])) for i in range(3))


class TerrainPBRFromBaseColor:
    CATEGORY = 'Terrain Tile Studio'
    FUNCTION = 'derive'
    RETURN_TYPES = ('IMAGE',)*7+('STRING',)
    RETURN_NAMES = MAP_NAMES+('parameters_json',)
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'image': ('IMAGE',),
            'normal_strength': ('FLOAT', {'default':4.0,'min':.1,'max':20.,'step':.1}),
            'height_contrast': ('FLOAT', {'default':1.15,'min':.1,'max':4.,'step':.05}),
            'ao_strength': ('FLOAT', {'default':1.25,'min':0.,'max':4.,'step':.05}),
            'roughness_base': ('FLOAT', {'default':.68,'min':0.,'max':1.,'step':.01}),
            'roughness_variation': ('FLOAT', {'default':.28,'min':0.,'max':1.,'step':.01}),
            'metallic': ('FLOAT', {'default':0.,'min':0.,'max':1.,'step':.01}),
            'invert_height': ('BOOLEAN', {'default':False}),
            'normal_format': (['OpenGL','DirectX'],)
        }}
    def derive(self,image,**parameters):
        results=[pbr_from_basecolor(a,**parameters) for a in image.detach().cpu().numpy()]
        outputs=[]
        for name in MAP_NAMES:
            arrays=[r[name] for r in results]
            arrays=[np.repeat(a[...,None],3,axis=-1) if a.ndim==2 else a for a in arrays]
            outputs.append(tensor(np.stack(arrays)))
        info={'specification':'Terrain Tile Studio 0.1.0 / v1.0','size':[int(image.shape[2]),int(image.shape[1])],
              'pbr':parameters,'boundary':'wrap','color_space':'BaseColor: sRGB; other maps: non-color data',
              'orm_channels':{'R':'AO','G':'Roughness','B':'Metallic'},'pbr_is_estimated':True}
        return (*outputs,json.dumps(info,ensure_ascii=False,indent=2))


class TerrainTileCheck:
    CATEGORY = 'Terrain Tile Studio'
    FUNCTION = 'tile'
    RETURN_TYPES = ('IMAGE','IMAGE')
    RETURN_NAMES = ('tile_2x2','tile_4x4')
    @classmethod
    def INPUT_TYPES(cls): return {'required':{'image':('IMAGE',)}}
    def tile(self,image):
        return image.repeat(1,2,2,1),image.repeat(1,4,4,1)


class TerrainExportBundle:
    CATEGORY = 'Terrain Tile Studio'
    FUNCTION = 'save'
    RETURN_TYPES = ()
    OUTPUT_NODE = True
    @classmethod
    def INPUT_TYPES(cls):
        required={name:('IMAGE',) for name in MAP_NAMES}
        required.update({'parameters_json':('STRING',{'forceInput':True}),
                         'band_ratio':('FLOAT',{'default':.05,'min':.01,'max':.30,'step':.01}),
                         'filename_prefix':('STRING',{'default':'TerrainTileStudio/material'})})
        return {'required':required}
    def save(self,parameters_json,band_ratio,filename_prefix,**maps):
        base=maps['BaseColor']
        folder,filename,counter,subfolder,_=folder_paths.get_save_image_path(filename_prefix,folder_paths.get_output_directory(),base.shape[2],base.shape[1])
        records=[]
        for index in range(len(base)):
            stem=f'{filename}_{counter:05d}_{index:02d}'
            destination=os.path.join(folder,stem)
            # Existing bundle directories are never overwritten.
            suffix=0
            while os.path.exists(destination):
                suffix+=1;destination=os.path.join(folder,f'{stem}_{suffix}')
            os.makedirs(destination)
            relative=os.path.relpath(destination,folder_paths.get_output_directory())
            for name in MAP_NAMES:
                a=maps[name][index].detach().cpu().numpy()
                if name in ('Height','Roughness','Metallic','AO'): a=a[:,:,0]
                pixels=np.rint(np.clip(a,0,1)*255).astype(np.uint8)
                Image.fromarray(pixels).save(os.path.join(destination,name+'.png'))
                records.append({'filename':name+'.png','subfolder':relative,'type':'output'})
            info=json.loads(parameters_json)
            info['seam']={'shift_x_ratio':.5,'shift_y_ratio':.5,'band_ratio':band_ratio,'mask_white_is_edit':True}
            with open(os.path.join(destination,'parameters.json'),'w',encoding='utf-8') as stream:
                json.dump(info,stream,ensure_ascii=False,indent=2)
        return {'ui':{'images':records}}


NODE_CLASS_MAPPINGS = {
    'TerrainPrepareSeam':TerrainPrepareSeam,
    'TerrainPBRFromBaseColor':TerrainPBRFromBaseColor,
    'TerrainTileCheck':TerrainTileCheck,
    'TerrainExportBundle':TerrainExportBundle,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    'TerrainPrepareSeam':'Terrain Prepare Seam · 接缝准备',
    'TerrainPBRFromBaseColor':'Terrain PBR From BaseColor · PBR 派生',
    'TerrainTileCheck':'Terrain Tile Check · 平铺检查',
    'TerrainExportBundle':'Terrain Export Bundle · 成套导出',
}
