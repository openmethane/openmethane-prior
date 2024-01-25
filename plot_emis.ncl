load "$NCARG_ROOT/lib/ncarg/nclscripts/wrf/WRFUserARW.ncl"
load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/shea_util.ncl"
load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/bootstrap.ncl"
load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/extval.ncl"

;------------------------------------------------------------------------
  
  ;Change the input emission file 
  f_emis   =  "./outputs/out-om-domain-info.nc"
  f1 = addfile(f_emis, "r") 
  
  
  ;Change the follwoing lines if your variables are diferent
  la = f1->LAT
  lo = f1->LON
  
  lat = la(0,:,:)
  lon = lo(0,:,:)        


   ;---Set some common resources
     res                       = True
     res@gsnDraw               = False    ; turn off draw
     res@gsnFrame              = False    ; turn off frame
     res@cnFillOn              = True     ; turn on contour fill
     res@cnLinesOn             = False    ; turn off contour lines
     res@cnLineLabelsOn        = False    ; turn off contour line labels
     res@gsnLeftString         = ""       ; turn off subtitles
     res@gsnRightString        = ""
     res@gsnCenterString       = ""
   
   ;---labelbar stuff
     res@lbLabelFontHeightF       = 0.015
      
   ; The plot size will be slightly adjusted internally to
   ; keep the aspect ratio of the map.
     res@vpXF                  = 0.08
     res@vpYF                  = 0.88
     res@vpWidthF              = 0.88
     res@vpHeightF             = 0.60
   
   ;---Necessary to put data on map correctly.
     res@sfXArray              = lon
     res@sfYArray              = lat
     res@gsnAddCyclic          = False
   
   ;---Copy common resources to resource lists for terrain and dbz plots
     tres                       = res
     dres                       = res      
   
   ;---set resources specific to terrain plot
    tres@cnLevelSelectionMode  = "ManualLevels" ;"ExplicitLevels"
    
    ;Change following lines for min and max of your emis files
    tres@cnMinLevelValF              = 0.
    tres@cnMaxLevelValF              = 10
    tres@cnLevelSpacingF             = .2
    tres@cnFillPalette               = "cmocean_deep" ; "WhViBlGrYeOrRe"   
    tres@lbOrientation         = "horizontal"
    
    ;Change the title of colour bar
    tres@lbTitleString         = "Methane emissions (kg km-2 hr-1)" 
    tres@lbTitleFontHeightF    = 0.015
    tres@lbLabelFontHeightF    = 0.02
    tres@lbTitleOffsetF        = -0.2
    tres@lbLabelAutoStride     = True
    tres@pmLabelBarOrthogonalPosF = 0.1    ; move labelbar away from plot
    tres@pmTickMarkDisplayMode = "Always"            ; nicer tickmarks   
    tres@mpFillOn              = False               ; turn off map fill  
    tres@mpDataBaseVersion     = "MediumRes"         ; better resolution
    tres@mpOutlineBoundarySets = "AllBoundaries"     ; more outlines
    tres@mpDataSetName         = "Earth..4"   
         
    ;Change following lines and set a range for min/max lat/lon if you want to zoom in on map 
    tres@mpMinLatF             = min(lat)    
    tres@mpMaxLatF             = max(lat)
    tres@mpMinLonF             = min(lon) 
    tres@mpMaxLonF             = max(lon)    
    
    ;Change the title of map       
;    tres@tiMainString = "total CH4 Emissions"
    tres@tiMainOffsetYF        = -0.03     
    tres@trGridType = "TriangularMesh"    

   wks  = gsn_open_wks("png","total" ) 
  emis = f1->OCH4_TOTAL
  hgt = dim_avg_n(emis(:,0,:,:),0) * 1e6  * 3600      
    hgt@lat2d = lat
  hgt@lon2d = lon

    ter_plot = gsn_csm_contour_map(wks,hgt,tres)    
    map = ter_plot
    lnres                  = True      ; resources for polylines
    lnres@gsLineThicknessF = 0.3; 2.0       ; 2x as thick           
 
    draw(map)
    frame(wks)

   wks  = gsn_open_wks("png","wetlands" ) 
  emis = f1->OCH4_WETLANDS
  hgt = dim_avg_n(emis(:,0,:,:),0) * 1e6  * 3600      
    hgt@lat2d = lat
  hgt@lon2d = lon

    ter_plot = gsn_csm_contour_map(wks,hgt,tres)    
    map = ter_plot
    lnres                  = True      ; resources for polylines
    lnres@gsLineThicknessF = 0.3; 2.0       ; 2x as thick           
 
    draw(map)
    frame(wks)
  
   wks  = gsn_open_wks("png","livestock" ) 
  emis2 = f1->OCH4_LIVESTOCK
  hgt = dim_avg_n( emis2(:,0,:,:),0) * 1e6  * 3600      
    hgt@lat2d = lat
  hgt@lon2d = lon

    ter_plot = gsn_csm_contour_map(wks,hgt,tres)    
    map = ter_plot
    lnres                  = True      ; resources for polylines
    lnres@gsLineThicknessF = 0.3; 2.0       ; 2x as thick           
 
    draw(map)
    frame(wks)

   wks  = gsn_open_wks("png","fugitive" ) 
  emis2 = f1->OCH4_FUGITIVE
  hgt = dim_avg_n(emis2(:,0,:,:),0) * 1e6  * 3600      
    hgt@lat2d = lat
  hgt@lon2d = lon

    ter_plot = gsn_csm_contour_map(wks,hgt,tres)    
    map = ter_plot
    lnres                  = True      ; resources for polylines
    lnres@gsLineThicknessF = 0.3; 2.0       ; 2x as thick           
 
    draw(map)
    frame(wks)

 
