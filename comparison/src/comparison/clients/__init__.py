"""The three frozen clients. Each answers one question — current
end-effector pose — in its adapter's most idiomatic way, then never
changes again: their line counts are measurements (AGENTS.md fairness
rules). All return the same dict shape: x,y,z,qx,qy,qz,qw,stamp_ns."""
