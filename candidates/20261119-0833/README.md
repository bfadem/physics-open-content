# Batch 20261119-0833

- Author model: `gemini-4-hydrogen`; blind solver: `gemini-3-flash-preview`
- Requested 30, attempted 23, **accepted 13**, rejected 10
- Model calls: 31; total tokens: 170978
- Stopped early: gemini-4-hydrogen: daily quota reached

## Rejections by stage

- author: 6
- instantiate: 3
- verify: 1

## Accepted (awaiting human review)

- `gen-20261119-0833-003` [interesting] Maximum power transfer in a DC resistor network: `V_0**2 * R_2 / (4 * (r_0 + R_1) * (r_0 + R_1 + R_2))`
- `gen-20261119-0833-005` [multi-step] DC circuits with resistors: `V_0**2 * R_2 * R_3**2 / ((r_0 + R_1) * (R_2 + R_3) + R_2 * R_3)**2`
- `gen-20261119-0833-006` [interesting] One-dimensional kinematics with constant acceleration and pursuit: `v_s*(t_r + (v_s + sqrt(v_s**2 + 2*a_p*v_s*t_r))/a_p)`
- `gen-20261119-0833-007` [plug-and-chug] Standing waves on a string under tension: `(n / (2 * L)) * sqrt(M_h * g * L / m_s)`
- `gen-20261119-0833-008` [multi-step] Bernoulli's equation, continuity, and projectile motion from a pressurized tank: `2*sqrt(y_0*(P_g + rho*g*(H - y_0))/(rho*g*(1 - (A_2/A_1)**2)))`
- `gen-20261119-0833-009` [interesting] standing waves on a string with a submerged hanging mass: `sqrt(M * g * (1 - rho_f / rho_b) / mu) / (2 * L)`
- `gen-20261119-0833-010` [plug-and-chug] conical pendulum: `2*pi*sqrt(L*cos(theta)/g)`
- `gen-20261119-0833-011` [multi-step] Conical pendulum: `m * (v**2 / L + sqrt((v**2 / L)**2 + 4 * g**2)) / 2`
- `gen-20261119-0833-012` [interesting] ballistic pendulum with a massive rod: `sqrt(2*g*L*(1 - cos(theta))*(m_b + m_p + m_r/3)*(m_b + m_p + m_r/2))/m_b`
- `gen-20261119-0833-013` [plug-and-chug] thin lens equation: `f*d_o/(f + d_o)`
- `gen-20261119-0833-015` [interesting] Two-block inclined plane system with kinetic friction: `sqrt(2*g*d*(m2 - m1*(sin(theta) + mu_k*cos(theta)))/(m1 + m2))`
- `gen-20261119-0833-016` [plug-and-chug] Conical pendulum period: `2*pi*sqrt(L*cos(theta)/g)`
- `gen-20261119-0833-022` [plug-and-chug] Conservation of angular momentum: `(M * R**2 * omega_i) / (M * R**2 + 2 * m * r**2)`

## Rejected

- `gen-20261119-0833-001` [author]  — RuntimeError: HTTP 503 from gemini-4-hydrogen: {
  "error": {
    "code": 503,
    "message": "This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try agai
- `gen-20261119-0833-002` [verify] torque and static equilibrium of a hinged beam with a supporting cable — ValueError: limit m_w->0: got g*m_b/(2*Abs(sin(theta))), expected g*m_b/(2*sin(theta)); limit theta->pi/2: got g*sqrt(L**2*m_b**2 + 4*L**2*m_b*m_w + 4*L**2*m_w**2 - 4*L*d*m_b*m_w - 8*L*d*m_w**2 + 4*d*
- `gen-20261119-0833-004` [instantiate] electric field on the axis of a uniformly charged ring — ValueError: unknown identifiers: ['e9']
- `gen-20261119-0833-014` [author]  — RuntimeError: HTTP 503 from gemini-4-hydrogen: {
  "error": {
    "code": 503,
    "message": "This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try agai
- `gen-20261119-0833-017` [author]  — TimeoutError: The read operation timed out
- `gen-20261119-0833-018` [author]  — RuntimeError: HTTP 503 from gemini-4-hydrogen: {
  "error": {
    "code": 503,
    "message": "This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try agai
- `gen-20261119-0833-019` [instantiate] Charging an RC circuit — ValueError: unknown identifiers: ['e']
- `gen-20261119-0833-020` [instantiate] capacitors and stored energy with dielectric insertion and charge sharing — ValueError: unknown identifiers: ['e']
- `gen-20261119-0833-021` [author]  — RuntimeError: HTTP 503 from gemini-4-hydrogen: {
  "error": {
    "code": 503,
    "message": "This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try agai
- `gen-20261119-0833-023` [author]  — RuntimeError: HTTP 503 from gemini-4-hydrogen: {
  "error": {
    "code": 503,
    "message": "This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try agai
