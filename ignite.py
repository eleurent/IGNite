# -*- coding: utf-8 -*-
"""
Created on Sat May 27 18:36:36 2017

@author: amine
"""

from urllib.request import urlopen, Request
import os
from PIL import Image
from lxml import etree
from pandas import DataFrame
from scipy.optimize import brentq
import math
from osgeo import gdal

class Map_IGN(object):
    DICT_FORMAT_PAP = {'A4':[21,29.7], 'A3':[29.7,42]}
    def __init__(self, long_ul, lat_ul, long_lr, lat_lr, zoom, echelle_imp = "1:25000"):
        self.long_ul = long_ul
        self.lat_ul = lat_ul
        self.long_lr = long_lr
        self.lat_lr = lat_lr
        self.zoom = zoom
        try:
            capabilities = Map_IGN.get_capabilities('capabilities.xml')
        except OSError:
            capabilities = Map_IGN.get_capabilities()
        self.MinTileCol = int(capabilities[1][str(zoom)]['MinTileCol'])
        self.MaxTileCol = int(capabilities[1][str(zoom)]['MaxTileCol'])
        self.MinTileRow = int(capabilities[1][str(zoom)]['MinTileRow'])
        self.MaxTileRow = int(capabilities[1][str(zoom)]['MaxTileRow'])
        self.ScaleDenominator = float(capabilities[1][str(zoom)]['ScaleDenominator'])
        self.TileHeight = int(capabilities[1][str(zoom)]['TileHeight'])
        self.TileWidth = int(capabilities[1][str(zoom)]['TileWidth'])
        self.TopLeftCorner_x = float(capabilities[1][str(zoom)]['TopLeftCorner'].split(' ')[0])
        self.TopLeftCorner_y = float(capabilities[1][str(zoom)]['TopLeftCorner'].split(' ')[1])
        self.TILEROW_ul,self.TILECOL_ul, self.TILEROW_lr,self.TILECOL_lr = self.coord_wmts()
        self.nt_x = self.TILECOL_lr-self.TILECOL_ul +1
        self.nt_y = self.TILEROW_lr-self.TILEROW_ul +1
        self.echelle_imp = echelle_imp
        self.taille_px_papier_cm = 2.54/96
        self.taille_px_reel_m = self.ScaleDenominator*0.00028*math.cos(Map_IGN.d2r(self.lat_ul))
        
    @staticmethod
    def load_capabilities(path_dst, file_name = 'capabilities.xml'):
        url_conf = "http://wxs.ign.fr/an7nvfzojv5wa96dsga5nk8w/geoportail/wmts?SERVICE=WMTS&REQUEST=GetCapabilities"
        req_conf = Request(url=url_conf,headers={'User-Agent':' Mozilla/5.0 (Windows NT 6.1; WOW64; rv:12.0) Gecko/20100101 Firefox/12.0'})
        xml_file = urlopen(req_conf)
        local_file = open(os.path.join(path_dst,file_name),'wb')
        local_file.write(xml_file.read())
        local_file.close() 
        
    @staticmethod
    def get_capabilities(file_name = None, layer = 'GEOGRAPHICALGRIDSYSTEMS.MAPS'):
        if file_name == None:
            Map_IGN.load_capabilities(os.getcwd())
            file_name = 'capabilities.xml'
            
        res = []
        tree = etree.parse(file_name)
        root = tree.getroot()
        # Dictionnaire des namespaces en remplacant celui de None par default
        dict_ns = root.nsmap
        dict_ns['default'] = dict_ns[None]
        del dict_ns[None]  
        
        #Selection de du Layer souhaité
        layer_elt_list = [elt for elt in root.findall('default:Contents/default:Layer',dict_ns) if elt.findall('ows:Identifier', dict_ns)[0].text=='GEOGRAPHICALGRIDSYSTEMS.MAPS' ]      
        
        layer_elts = layer_elt_list[0].findall('default:TileMatrixSetLink',dict_ns)[0].getchildren() #Returns list elts[TileMatrixSet, TileMatrixSetLimits]
        
        # Alimentation du TileMatrixset dans layer
        d = {}
        d[layer_elts[0].tag.split('}')[1]] = layer_elts[0].text
        res.append(d)
        
        # Alimentation des zooms
        d1 = {}
        for elt in layer_elts[1].findall('default:TileMatrixLimits', dict_ns):  #Parcourir tous les niveaux de zooms dispo
            zoom = elt.findall('default:TileMatrix',dict_ns)[0].text
            d1[zoom] = {}
            for x in elt.getchildren()[1:]:
                d1[zoom][x.tag.split('}')[1]] = x.text
            
            #Alimentation desTitleMatrixSet
            TMS = [elt for elt in root.findall('default:Contents/default:TileMatrixSet',dict_ns) if elt.findall('ows:Identifier', dict_ns)[0].text== layer_elts[0].text]
            TMS_select = [elt for elt in TMS[0].findall('default:TileMatrix',dict_ns) if elt.find('ows:Identifier', dict_ns).text == zoom]
            for y in TMS_select[0].getchildren()[1:]:
                d1[zoom][y.tag.split('}')[1]] = y.text               
        res.append(DataFrame(d1))
        return res
        
    @staticmethod
    def d2r(angle_deg):
        degre = float(angle_deg.split('°')[0])
        minutes = float(angle_deg.split('°')[1].split("'")[0])
        secondes = float(angle_deg.split('°')[1].split("'")[1])
     
        angle_dec = degre + (minutes/60) + (secondes/3600)
        
        return math.radians(angle_dec)
        
    def coord_wmts(self):
        long_ul_rad = Map_IGN.d2r(self.long_ul)
        lat_ul_rad = Map_IGN.d2r(self.lat_ul)
        long_lr_rad = Map_IGN.d2r(self.long_lr)
        lat_lr_rad = Map_IGN.d2r(self.lat_lr)        
        
        ## Projection Mercator
        a = 6378137.0 #a: rayon équatorial (demi grand axe) de l’ellipsoïde
        X_ul= a * long_ul_rad
        Y_ul= a * math.log(math.tan(lat_ul_rad/2 + math.pi/4))
        X_lr= a * long_lr_rad
        Y_lr= a * math.log(math.tan(lat_lr_rad/2 + math.pi/4))

        renderingpixelsize = 0.00028
        
        taille_tuile = self.ScaleDenominator*renderingpixelsize*self.TileHeight
        
        TILECOL_ul = int((X_ul-self.TopLeftCorner_x)/taille_tuile)
        TILEROW_ul = int((self.TopLeftCorner_y-Y_ul)/taille_tuile)
        TILECOL_lr = int((X_lr-self.TopLeftCorner_x)/taille_tuile)
        TILEROW_lr = int((self.TopLeftCorner_y-Y_lr)/taille_tuile)
    
        return TILEROW_ul,TILECOL_ul, TILEROW_lr,TILECOL_lr
        
    def get_ullr_tile(self):
        #Constantes
        a = 6378137.0 #a: rayon équatorial (demi grand axe) de l’ellipsoïde
        renderingpixelsize = 0.00028    
        taille_tuile = self.ScaleDenominator*renderingpixelsize*self.TileHeight
        
        ## Calcul de X et Y a partir de TILECOL et TILEROW
        X_ul = (self.TILECOL_ul*taille_tuile) + self.TopLeftCorner_x      
        X_lr = ((self.TILECOL_lr+1)*taille_tuile) + self.TopLeftCorner_x
        Y_ul = self.TopLeftCorner_y - (self.TILEROW_ul*taille_tuile)
        Y_lr = self.TopLeftCorner_y - ((self.TILEROW_lr+1)*taille_tuile)
        
        ##Calcul longitudes et latitudes en deg
        ul_x = math.degrees(X_ul/a)
        lr_x = math.degrees(X_lr/a)        
        def uly(x):
            return Y_ul - a * math.log(math.tan(x/2 + math.pi/4))
        def lry(x):
            return Y_lr - a * math.log(math.tan(x/2 + math.pi/4))
        ul_y = math.degrees(brentq(uly, 0, math.pi/2))
        lr_y = math.degrees(brentq(lry, 0, math.pi/2))
        
        return [ul_x, ul_y, lr_x, lr_y]
            
            
    def generate_map(self,file_name='tuiles_IGN'):
        try:
            os.mkdir(file_name)
        except FileExistsError:
            pass
        
        map_IGN = Image.new('RGB', (256*self.nt_x,256*self.nt_y))
            
        for x in range(self.TILECOL_ul, min(self.TILECOL_ul+self.nt_x,self.MaxTileCol)):
            for y in range(self.TILEROW_ul, min(self.TILEROW_ul +self.nt_y, self.MaxTileRow)):
                url_test = "https://wxs.ign.fr/an7nvfzojv5wa96dsga5nk8w/geoportail/wmts?layer=GEOGRAPHICALGRIDSYSTEMS.MAPS&style=normal&tilematrixset=PM&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&"+"TileMatrix=%s&TileCol=%s&TileRow=%s"%(self.zoom, x,y)
                
                req = Request(url=url_test,data=b'None',headers={'User-Agent':' Mozilla/5.0 (Windows NT 6.1; WOW64; rv:12.0) Gecko/20100101 Firefox/12.0'})
                
                img = urlopen(req)
                path_tuile_local = os.path.join(os.getcwd(),file_name,'%s_%s.jpg'%(x-self.TILECOL_ul,y-self.TILEROW_ul))
                tuile_local = open(path_tuile_local, 'wb')
                tuile_local.write(img.read())
                tuile_local.close()
                
                img= Image.open(path_tuile_local)
                map_IGN.paste(img, ((x-self.TILECOL_ul)*256,(y-self.TILEROW_ul)*256))
                map_IGN.save('map_IGN.jpg',"JPEG")         
        return map_IGN
        
    def set_georeference (self, dstName, sourceDS, frmt = "GTiff"):
        opt = gdal.TranslateOptions(format= frmt,outputBounds= self.get_ullr_tile(),outputSRS="WGS84")
        gdal.Translate(dstName,sourceDS, options = opt)
        
    def resize(self, img):
        ech = int(self.echelle_imp.split(':')[1])
        new_size_x = int(img.size[0]*self.taille_px_reel_m*100/ech/self.taille_px_papier_cm)
        new_size_y = int(img.size[1]*self.taille_px_reel_m*100/ech/self.taille_px_papier_cm)
        new_img = img.resize((new_size_x, new_size_y), Image.ANTIALIAS)
        new_img.save('resized_image.jpg', quality =95)
        return new_img
        
    def crop(self,img, frt_pap = 'A4', marge_imp = 0.95):      
        x_pap_px = marge_imp*self.DICT_FORMAT_PAP[frt_pap][0]/self.taille_px_papier_cm
        y_pap_px = marge_imp*self.DICT_FORMAT_PAP[frt_pap][1]/self.taille_px_papier_cm
        
        x_img_px = img.size[0]
        y_img_px = img.size[1]

        ### decoupage portrait
        nb_por_x = math.ceil(x_img_px/x_pap_px)
        nb_por_y = math.ceil(y_img_px/y_pap_px)
        nb_feuille_por = nb_por_x*nb_por_y
        #decoupage paysage
        nb_pay_x = math.ceil(x_img_px/y_pap_px)
        nb_pay_y = math.ceil(y_img_px/x_pap_px)
        nb_feuille_pay = nb_pay_x*nb_pay_y
        
        list_coord = []

        if nb_feuille_por < nb_feuille_pay:
            file_name = 'for_imp_portrait'
            try:
                os.mkdir(file_name)
            except FileExistsError:
                pass
            for i in range(nb_por_x):
                for j in range(nb_por_y):
                    res = (int(x_pap_px*i),int(y_pap_px*j),min(int(x_pap_px*(i+1)),x_img_px),min(int(y_pap_px*(j+1)),y_img_px)) 
                    img.crop(res).save(os.path.join(os.getcwd(),file_name,'%s_%s.jpg'%(str(i), str(j))))
                    list_coord.append(res)            
        else:
            file_name = 'for_imp_paysage'
            try:
                os.mkdir(file_name)
            except FileExistsError:
                pass
            for i in range(nb_pay_x):
                for j in range(nb_pay_y):
                    res = (int(y_pap_px*i),int(x_pap_px*j),min(int(y_pap_px*(i+1)),x_img_px),min(int(x_pap_px*(j+1)),y_img_px)) 
                    img.crop(res).save(os.path.join(os.getcwd(),file_name,'%s_%s.jpg'%(str(i), str(j))))
                    list_coord.append(res)
        return list_coord
                           
if __name__ == '__main__':
    carte = Map_IGN("-1.33°0'0","43°10'50.00","-0.55°0'00.00", "42°52'20.00",15, echelle_imp = "1:25000")
    print(carte.nt_x*carte.nt_y)   
#    img = carte.generate_map()
#    resized_img = carte.resize(img)
#    carte.crop(resized_img, frt_pap='A3')
#    carte.set_georeference("map_IGN_geo.tiff", "map_IGN.jpg", frmt = "GTiff")
#    carte.set_georeference("map_IGN_geo.jpg", "map_IGN.jpg", frmt = "JPEG")
    carte.set_georeference("pyr_geo.pdf", "map_IGN.jpg", frmt = "PDF")

#    #img = Image.open('map_IGN_z15.jpg')
#    resized_img = carte.resize(img)
#    #img_tmp = Image.open('resized_image.jpg')
#    t = carte.crop(resized_img, frt_pap='A4')