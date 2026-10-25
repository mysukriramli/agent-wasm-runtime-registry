(module
  (func $planar_distance_sq (export "planar_distance_sq") (param $lat1 f32) (param $lon1 f32) (param $lat2 f32) (param $lon2 f32) (result f32)
    (local $dlat f32)
    (local $dlon f32)
    
    local.get $lat1
    local.get $lat2
    f32.sub
    local.set $dlat
    
    local.get $lon1
    local.get $lon2
    f32.sub
    local.set $dlon
    
    ;; (dlat * dlat) + (dlon * dlon)
    local.get $dlat
    local.get $dlat
    f32.mul
    local.get $dlon
    local.get $dlon
    f32.mul
    f32.add
  )
)
