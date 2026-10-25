(module
  (func $estimate_tokens (export "estimate_tokens") (param $byte_length i32) (param $word_count i32) (result i32)
    ;; Approximation formula: (word_count * 4 + byte_length) / 6
    local.get $word_count
    i32.const 4
    i32.mul
    local.get $byte_length
    i32.add
    i32.const 6
    i32.div_u
  )
)
