"""School-only art pass. Existing gameplay references and openings are preserved."""
import json
from pathlib import Path
import unreal as u

MAP='/Game/ZombieSeasons/Maps/Development/L_ZS_School_Expedition'
ROOT='/Game/ZombieSeasons/SchoolA2'
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
assert not levels.is_in_play_in_editor()
assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
assert levels.load_level(MAP)
original={a.get_actor_label():a for a in actors.get_all_level_actors()}
cube=u.load_asset('/Engine/BasicShapes/Cube')
lib=u.MaterialEditingLibrary
created=[]

def plain(name,color,rough=.8):
    path=ROOT+'/Materials/'+name
    if u.EditorAssetLibrary.does_asset_exist(path):return u.load_asset(path)
    m=u.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
    n=lib.create_material_expression(m,u.MaterialExpressionConstant3Vector)
    n.set_editor_property('constant',u.LinearColor(*color,1))
    assert lib.connect_material_property(n,'',u.MaterialProperty.MP_BASE_COLOR)
    r=lib.create_material_expression(m,u.MaterialExpressionConstant);r.set_editor_property('r',rough)
    assert lib.connect_material_property(r,'',u.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(m);assert u.EditorAssetLibrary.save_loaded_asset(m)
    return m

def textured(name,texture,scale,tint):
    path=ROOT+'/Materials/'+name
    if u.EditorAssetLibrary.does_asset_exist(path):return u.load_asset(path)
    m=u.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
    t=lib.create_material_expression(m,u.MaterialExpressionTextureObject)
    tex=u.load_asset(texture);assert tex,texture
    t.set_editor_property('texture',tex)
    f=lib.create_material_expression(m,u.MaterialExpressionMaterialFunctionCall)
    f.set_material_function(u.load_asset('/Engine/Functions/Engine_MaterialFunctions01/Texturing/WorldAlignedTexture'))
    size=lib.create_material_expression(m,u.MaterialExpressionConstant3Vector)
    size.set_editor_property('constant',u.LinearColor(scale,scale,scale,1))
    assert lib.connect_material_expressions(t,'',f,'TextureObject')
    assert lib.connect_material_expressions(size,'',f,'TextureSize')
    mul=lib.create_material_expression(m,u.MaterialExpressionMultiply)
    color=lib.create_material_expression(m,u.MaterialExpressionConstant3Vector)
    color.set_editor_property('constant',u.LinearColor(*tint,1))
    assert lib.connect_material_expressions(f,'XYZ Texture',mul,'A')
    assert lib.connect_material_expressions(color,'',mul,'B')
    assert lib.connect_material_property(mul,'',u.MaterialProperty.MP_BASE_COLOR)
    rough=lib.create_material_expression(m,u.MaterialExpressionConstant);rough.set_editor_property('r',.82)
    lib.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(m);assert u.EditorAssetLibrary.save_loaded_asset(m)
    return m

def spawn(cls,name,pos,yaw=0):
    name='A2_'+name
    if name in original:return original[name]
    a=actors.spawn_actor_from_class(cls,u.Vector(*pos),u.Rotator(pitch=0,yaw=yaw,roll=0))
    assert a,name
    a.set_actor_label(name);a.set_folder_path('SchoolA2');a.set_editor_property('tags',[u.Name('ZS.School.A2')])
    original[name]=a;created.append(name)
    return a

def box(name,pos,size,mat,collision=True,yaw=0):
    a=spawn(u.StaticMeshActor,name,pos,yaw);c=a.static_mesh_component
    c.set_static_mesh(cube);c.set_material(0,mat)
    c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    a.set_actor_scale3d(u.Vector(*(v/100 for v in size)))
    return a

def prop(name,path,pos,yaw=0):
    mesh=u.load_asset(path);assert mesh,path
    a=spawn(u.StaticMeshActor,name,pos,yaw);c=a.static_mesh_component;c.set_static_mesh(mesh)
    c.set_collision_profile_name('BlockAll')
    u.log(f'A2_PROP {name} bounds={mesh.get_bounds()}')
    return a

def sign(name,text,pos,yaw=0,width=180,height=35,size=12):
    plate=box(name+'_Support',pos,(3,width,height),green,False,yaw)
    import math
    facing=(math.cos(math.radians(yaw)),math.sin(math.radians(yaw)))
    p=(pos[0]+facing[0]*2,pos[1]+facing[1]*2,pos[2])
    a=spawn(u.TextRenderActor,name,p,yaw)
    c=a.get_component_by_class(u.TextRenderComponent)
    c.set_text(text);c.set_world_size(size)
    c.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
    c.set_vertical_alignment(u.VerticalTextAligment.EVRTA_TEXT_CENTER)
    c.set_text_render_color(u.Color(234,229,205,255))
    return a

concrete=textured('M_WornConcrete','/Game/StarterContent/Textures/T_Concrete_Poured_D',180,(.7,.71,.66))
plaster=textured('M_PaintedPlaster','/Game/StarterContent/Textures/T_Concrete_Poured_D',220,(1.35,1.29,1.13))
floor=textured('M_ServiceTile','/Game/StarterContent/Textures/T_Concrete_Tiles_D',160,(.66,.72,.69))
wood=textured('M_GymParquet','/Game/StarterContent/Textures/T_Wood_Floor_Walnut_D',220,(1.25,1.1,.85))
steel=textured('M_BrushedMetal','/Game/StarterContent/Textures/T_Metal_Steel_D',100,(.6,.66,.64))
asphalt=textured('M_Courtyard','/Game/AsphaltMat/Textures/T_AsphaltMat9_basecolor',400,(.6,.65,.67))
green=plain('M_MunicipalGreen',(.075,.14,.13));canvas=plain('M_Canvas',(.22,.27,.2))
paper=plain('M_Paper',(.71,.67,.53));white=plain('M_CourtPaint',(.65,.63,.49))
dark=plain('M_Radio',(.018,.025,.022),.4);amber=plain('M_Amber',(.65,.3,.04))

# Keep the original geometry and combat lanes, but give each surface a function.
for name,a in list(original.items()):
    if name.startswith('A2_'):continue
    if isinstance(a,u.TextRenderActor):a.get_component_by_class(u.TextRenderComponent).set_visibility(False)
    if isinstance(a,u.StaticMeshActor):
        c=a.static_mesh_component
        if name=='A1_Ground':c.set_material(0,asphalt)
        elif name=='Gym_Floor':c.set_material(0,wood)
        elif name=='Comptoir_Cuisine':c.set_material(0,steel)
        elif name in ['Commande_Liaison','Poste_Retour']:c.set_material(0,dark)
        elif 'Glass' in name:continue
        elif 'Roof' in name:c.set_material(0,plaster)
        elif name in ['Passage_Lateral','Raccourci']:c.set_material(0,green)
        elif 'Barriere' in name:c.set_material(0,green)
        else:c.set_material(0,concrete)
        # A continuous washable lower wall with a plaster finish above it.
        scale=a.get_actor_scale3d();pos=a.get_actor_location()
        if ('_' in name and min(scale.x,scale.y)<=.22 and scale.z>=2.5 and name not in ['Passage_Lateral','Raccourci']):
            c.set_material(0,plaster)
            box(name+'_Soubassement',(pos.x,pos.y,65),(scale.x*100+1,scale.y*100+1,130),green,False)

for name,pos,size in [('Cuisine',(-1000,-800,2),(1180,1180,4)),('Service',(-200,-100,2),(380,2580,4)),('Accueil',(400,-700,2),(780,1380,4)),('Rangement',(-400,1600,2),(780,780,4))]:
    box('Sol_'+name,pos,size,floor)

# Mounted, readable signs; no development vocabulary inside the fiction.
sign('Entree','ÉCOLE MUNICIPALE',( -1613,-800,325),180,330,45,20)
sign('Cuisine','CUISINE  /  ENTRÉE DE SERVICE',(-1614,-400,220),180,260,32,11)
sign('Accueil','ACCUEIL  →',(-410,-850,235),180,170,32,15)
sign('Bureau','ACCUEIL  /  RADIO',(-14,-870,250),180,240,35,14)
sign('GroupeB','GROUPE B  ·  ATTENTE DES TRANSPORTS',(1600,1986,285),-90,600,65,26)
sign('Sortie','SORTIE  →',(3186,1320,245),180,165,40,17)
sign('Service','COUR DE LIVRAISON',(4000,-1184,255),90,280,40,16)
sign('Retour','POINT RADIO',(-3250,-1519,195),90,180,36,14)
sign('PorteLaterale','PASSAGE DE SERVICE',(-15,1600,245),180,260,35,14)

# Registration desk and actual radio controls, built at furniture scale.
relay=original['Commande_Liaison'];relay.set_actor_location(u.Vector(675,-900,110),False,False)
relay.set_actor_scale3d(u.Vector(.3,.58,.33))
box('BureauPlateau',(675,-900,88),(100,180,7),wood)
for x in [635,715]:
    for y in [-975,-825]:box(f'BureauPied{x}_{y}',(x,y,43),(5,5,86),steel)
for i in range(7):box('RadioGrille'+str(i),(658,-920+i*5,110),(1,2,22),steel,False)
box('RadioVoyant',(658,-881,117),(1,5,3),amber,False)
box('RadioAntenne',(679,-919,147),(1,1,45),steel,False)
for i in range(3):box('FicheAccueil'+str(i),(645,-851+i*12,92),(23,17,0.3),paper,False,yaw=i*9)
prop('ChaiseAccueil','/Game/StarterContent/Props/SM_Chair',(560,-900,4),90)
prop('EtagereCuisine','/Game/StarterContent/Props/SM_Shelf',(-1450,-1250,4),90)
prop('BancCour','/Game/Street_Props_Pack_V1/Mesh/SM_Bench',(-3450,-550,0),90)
prop('PaletteLivraison','/Game/Street_Props_Pack_V1/Mesh/SM_Pallet',(-1950,-1800,0),0)

# Gym court markings leave both bypasses open.
for name,pos,size in [('Sud',(1650,260,5),(2400,5,.3)),('Nord',(1650,1450,5),(2400,5,.3)),('Ouest',(450,855,5),(5,1190,.3)),('Est',(2850,855,5),(5,1190,.3)),('Milieu',(1650,855,5),(5,1190,.3))]:
    box('Ligne'+name,pos,size,white,False)
# Replace the anonymous central block with recognisable folded bleachers, same footprint.
original['Gradins_Replies'].set_actor_hidden_in_game(True)
original['Gradins_Replies'].set_actor_enable_collision(False)
for i in range(3):
    box('GradinAssise'+str(i),(1500,935+i*100,45+i*45),(650,90,10),wood)
    for x in [1220,1500,1780]:box(f'GradinPied{i}_{x}',(x,935+i*100,(45+i*45)/2),(8,80,45+i*45),steel)
# Emergency beds and grouped belongings explain the occupied school.
for i,x in enumerate([650,1050,1450,2050,2450,2850]):
    y=1850
    box(f'LitToile{i}',(x,y,44),(175,62,8),canvas)
    for dx in [-78,78]:
        for dy in [-25,25]:box(f'LitPied{i}_{dx}_{dy}',(x+dx,y+dy,22),(4,4,44),steel)
    box(f'LitOreiller{i}',(x-62,y,51),(35,52,10),paper,False)
    box(f'EffetsPersonnels{i}',(x+85,y-58,18),(35,25,36),green)
for n in ['Attente_B_Volume_0','Attente_B_Volume_1','Attente_B_Volume_2']:
    original[n].set_actor_hidden_in_game(True);original[n].set_actor_enable_collision(False)

# Visible fixtures, windows high above combat sightlines, a modest exterior perimeter.
for i,(x,y) in enumerate([(650,600),(2200,1200),(700,1500),(1700,1500),(2700,1500)]):
    prop('Luminaire'+str(i),'/Game/StarterContent/Props/SM_Lamp_Ceiling',(x,y,660),0)
for i,x in enumerate([500,1100,1700,2300,2900]):
    box('FenetreCadre'+str(i),(x,1985,525),(400,8,170),green,False)
    box('FenetreVerre'+str(i),(x,1979,525),(378,5,148),plain('M_VerreDepoli',(.25,.34,.36),.25),False)
    box('FenetreMontant'+str(i),(x,1974,525),(6,4,150),steel,False)
for i in range(5):
    prop('Arbuste'+str(i),'/Game/StarterContent/Props/SM_Bush',(-3860,-1500+i*700,0),i*37)

# Two entry enemies wake only after the player's deliberate approach and a grace period.
scenario=original['Scenario_Ecole_B']
scenario.set_editor_property('entry_enemies',[original['Infecte_0'],original['Infecte_1']])
for n,pos in [('Infecte_0',(-1250,-1100,110)),('Infecte_1',(-1300,-550,110))]:
    original[n].set_actor_location(u.Vector(*pos),False,False)
for i,x in enumerate([600,1100,1800,2400,2900],start=2):
    original['Infecte_'+str(i)].set_actor_location(u.Vector(x,1700,110),False,False)
for a in original.values():
    if isinstance(a,u.RecastNavMesh):
        a.set_editor_property('runtime_generation',u.RuntimeGenerationType.DYNAMIC)
        a.set_editor_property('force_rebuild_on_load',True)
assert levels.save_current_level()
report=Path(u.Paths.project_saved_dir())/'SchoolA1'/'art_a2.json'
report.write_text(json.dumps({'added':created,'map':MAP,'status':'saved_requires_runtime_check'},ensure_ascii=False,indent=2),encoding='utf-8')
u.log('SCHOOL_A2_SAVED '+str(len(created)))
