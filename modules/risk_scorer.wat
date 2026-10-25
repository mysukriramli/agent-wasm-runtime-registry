(module
  (func $calculate_risk (export "calculate_risk") (param $epss f32) (param $cvss f32) (param $w_epss f32) (param $w_cvss f32) (result f32)
    (local $numerator f32)
    (local $denominator f32)
    
    ;; numerator = (epss * w_epss) + (cvss * w_cvss)
    local.get $epss
    local.get $w_epss
    f32.mul
    local.get $cvss
    local.get $w_cvss
    f32.mul
    f32.add
    local.set $numerator
    
    ;; denominator = w_epss + w_cvss
    local.get $w_epss
    local.get $w_cvss
    f32.add
    local.set $denominator
    
    ;; result = numerator / denominator
    local.get $numerator
    local.get $denominator
    f32.div
  )
)
