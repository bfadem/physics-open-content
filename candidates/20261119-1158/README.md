# Batch 20261119-1158

- Requested 30, attempted 30, **accepted 16**, rejected 14, skipped (model unavailable) 0
- Ran to completion

## Engines

| engine | roles | calls | tokens | state |
|---|---|---|---|---|
| `gemini:gemini-4-hydrogen` | author | 0 | 0 | exhausted (gemini:gemini-4-hydrogen: daily quota reached) |
| `gemini:gemini-3-flash-preview` | author, solver | 2 | 25008 | exhausted (gemini:gemini-3-flash-preview: daily quota reached) |
| `gemini:gemini-3.5-flash-lite` | author, solver | 30 | 25033 | ready |
| `gemini:gemma-4-31b-it` | author, solver | 0 | 0 | ready |
| `gemini:gemini-3.1-flash-lite` | solver | 20 | 4665 | ready |

## Rejections by stage

- agreement: 2
- dedupe: 2
- precheck: 8
- verify: 2

## Accepted (awaiting human review)

- `gen-20261119-1158-001` [plug-and-chug] Moment of inertia of a solid cylinder: `0.5 * M_cyl * R_cyl**2` (gemini:gemini-3-flash-preview / gemini:gemini-3.5-flash-lite)
- `gen-20261119-1158-002` [multi-step] Volume of an ideal gas in a piston-cylinder system: `(n_mol * R_gas * T_f) / (P_ext + (m_p * g / area_p))` (gemini:gemini-3-flash-preview / gemini:gemini-3.5-flash-lite)
- `gen-20261119-1158-004` [plug-and-chug] Doppler effect for a moving source: `frequency_source * speed_sound / (speed_sound - speed_source)` (gemini:gemini-3.5-flash-lite / gemini:gemini-3.1-flash-lite)
- `gen-20261119-1158-007` [plug-and-chug] Doppler effect for sound: `f_0*v_c/(v_c - v_s)` (gemini:gemini-3.5-flash-lite / gemini:gemini-3.1-flash-lite)
- `gen-20261119-1158-008` [multi-step] simple harmonic motion of a block on a spring: `A*sqrt(k/m)` (gemini:gemini-3.5-flash-lite / gemini:gemini-3.1-flash-lite)
- `gen-20261119-1158-009` [interesting] Uniform circular motion on a conical pendulum: `m*g/cos(theta)` (gemini:gemini-3.5-flash-lite / gemini:gemini-3.1-flash-lite)
- `gen-20261119-1158-015` [interesting] DC circuits with resistors: `V_source^2 / (R_1 + (R_2 * R_3) / (R_2 + R_3))` (gemini:gemini-3.5-flash-lite / gemini:gemini-3.1-flash-lite)
- `gen-20261119-1158-016` [plug-and-chug] Snell's law refraction angle: `asin(n_1*sin(theta_1)/n_2)` (gemini:gemini-3.5-flash-lite / gemini:gemini-3.1-flash-lite)
- `gen-20261119-1158-017` [multi-step] Rolling without slipping down an inclined plane: `sqrt(4*g*L*sin(theta)/3)` (gemini:gemini-3.5-flash-lite / gemini:gemini-3.1-flash-lite)
- `gen-20261119-1158-018` [interesting] fluid statics and buoyancy: `M / (rho_L * A)` (gemini:gemini-3.5-flash-lite / gemini:gemini-3.1-flash-lite)
- `gen-20261119-1158-020` [multi-step] Coulomb's law force between three point charges in a line: `k_e*q_2*Abs(q_3/(x_b - x_a)^2 - q_1/x_a^2)` (gemini:gemini-3.5-flash-lite / gemini:gemini-3.1-flash-lite)
- `gen-20261119-1158-022` [plug-and-chug] conical pendulum: `m * g / cos(theta)` (gemini:gemini-3.5-flash-lite / gemini:gemini-3.1-flash-lite)
- `gen-20261119-1158-023` [multi-step] Fluid flow through a horizontal pipe with a constriction using Bernoulli's equation and continuity: `0.5*rho*v1^2*((A1/A2)^2 - 1)` (gemini:gemini-3.5-flash-lite / gemini:gemini-3.1-flash-lite)
- `gen-20261119-1158-024` [interesting] Standing waves on a vertical string with a hanging mass: `n/(2*L)*sqrt(M*g*L/m)` (gemini:gemini-3.5-flash-lite / gemini:gemini-3.1-flash-lite)
- `gen-20261119-1158-029` [multi-step] First law of thermodynamics for an ideal gas undergoing an isothermal expansion: `n_moles*R*T*log(V_final/V_initial)` (gemini:gemini-3.5-flash-lite / gemini:gemini-3.1-flash-lite)
- `gen-20261119-1158-030` [interesting] thin lens imaging and object translation: `delta_u*f^2/(u - f)^2` (gemini:gemini-3.5-flash-lite / gemini:gemini-3.1-flash-lite)

## Rejected

- `gen-20261119-1158-003` [precheck] Electric field of a finite line charge — ValueError: no given value for ['E_mag']
- `gen-20261119-1158-005` [precheck] conical pendulum — ValueError: no given value for ['omega']
- `gen-20261119-1158-006` [precheck] Magnetic force on a moving charge in crossed fields — ValueError: reserved identifier 'E'
- `gen-20261119-1158-010` [precheck] orbital motion and gravitation — ValueError: no given value for ['v']
- `gen-20261119-1158-011` [verify] RC circuit discharging — ValueError: dimensions: unknown units: ['F']
- `gen-20261119-1158-012` [precheck] Orbital motion of a satellite in a circular orbit — ValueError: no given value for ['v']
- `gen-20261119-1158-013` [precheck] Torque and static equilibrium on a uniform beam — ValueError: no given value for ['T']
- `gen-20261119-1158-014` [verify] RC circuit discharging time — ValueError: dimensions: unknown units: ['F']
- `gen-20261119-1158-019` [precheck] physical pendulum — ValueError: no given value for ['T']
- `gen-20261119-1158-021` [agreement] Doppler effect for a moving source and observer — ValueError: author and blind solver disagree: differ at a test point: -2.8555+0j vs 11.8366+0j
- `gen-20261119-1158-025` [dedupe] Snell's law refraction — ValueError: duplicate of gen-20261119-1158-016
- `gen-20261119-1158-026` [dedupe] conical pendulum — ValueError: duplicate of gen-20261119-1158-009
- `gen-20261119-1158-027` [agreement] conical pendulum with rotating suspension axis — ValueError: author and blind solver disagree: differ at a test point: 1.13143+0j vs 1.02083+0j
- `gen-20261119-1158-028` [precheck] capacitors and stored energy — ValueError: no given value for ['U']
