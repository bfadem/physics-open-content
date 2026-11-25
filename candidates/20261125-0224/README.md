# Batch 20261125-0224

- Request: `requests/2026-11-24_impulse-first_newton-2nd-rotational.json` (copied to `request.json`)
- State: 40 concepts covered through `newton-2nd-rotational`, 8 forbidden; calculus ['graphical-area', 'graphical-slope', 'trig-decomposition']; representations ['free-body-diagram', 'momentum-vector-diagram']
- Targets: angular position, velocity and acceleration, torque, rotational inertia (moment of inertia), Newton's second law for rotation: net torque equals rotational inertia times angular acceleration
- Checks: 1-8 (curriculum, lexical, pedagogy included)
- Requested 15, attempted 16, **accepted 14**, rejected 2, skipped (model unavailable) 0
- Ran to completion

## Engines

| engine | roles | calls | tokens | state |
|---|---|---|---|---|
| `gemini:gemini-4-hydrogen` | author | 3 | 62817 | ready |
| `groq:openai/gpt-oss-120b` | author, solver | 1 | 4394 | ready |
| `gemini:gemini-3-flash-preview` | author, solver | 14 | 84664 | ready |
| `gemini:gemini-3.5-flash-lite` | author, solver | 0 | 0 | ready |
| `gemini:gemma-4-31b-it` | author, solver | 0 | 0 | ready |
| `groq:qwen/qwen3.8-27b` | solver | 0 | 0 | ready |
| `gemini:gemini-3.1-flash-lite` | solver | 0 | 0 | ready |
| `groq:openai/gpt-oss-20b` | solver | 0 | 0 | ready |

## Rejections by stage

- author: 1
- precheck: 1

## Accepted (awaiting human review)

- `gen-20261125-0224-001` [plug-and-chug] angular acceleration from angular speed and time: `omega / t` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261125-0224-002` [plug-and-chug] angular speed from linear speed and radius: `v / r` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261125-0224-003` [plug-and-chug] torque from a force applied at an angle: `r * F * sin(theta)` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261125-0224-004` [plug-and-chug] rotational inertia of two point masses: `m_1 * r_1**2 + m_2 * r_2**2` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261125-0224-005` [plug-and-chug] rotational inertia of a uniform solid disk: `m * R**2 / 2` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261125-0224-006` [plug-and-chug] angular acceleration from net torque and rotational inertia: `tau / I_wheel` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261125-0224-007` [plug-and-chug] net torque from rotational inertia and angular acceleration: `I_turb * alpha` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261125-0224-010` [multi-step] inclined plane block coupled to a rotating pulley: `sqrt(2*d*(I_p + m*R**2)/(m*g*R**2*(sin(theta) - mu_k*cos(theta))))` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261125-0224-011` [multi-step] rotational inertia and uniform circular motion of a two-mass rod: `m_2*r_2**3*(F*t_0*sin(phi))**2/(m_1*r_1**2 + m_2*r_2**2)**2` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261125-0224-012` [multi-step] rotational equilibrium of a pivoted rod held by a spring: `(m*g*L*cos(phi))**2/(2*k*d**2*sin(theta)**2)` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261125-0224-013` [multi-step] two-stage angular acceleration and braking of a flywheel: `sqrt(2*I_w*theta_1/(F*R))*(1 + F/(mu_k*F_N))` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261125-0224-014` [multi-step] stepped pulley with two hanging blocks: `(m_2*r_2 - m_1*r_1)*(r_1 + r_2)*g*t_0**2/(2*(I_d + m_1*r_1**2 + m_2*r_2**2))` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261125-0224-015` [interesting] Newton's second law for rotation and pivot reaction force: `M*g*(M*L**2 + 4*m*(3*d**2 - 3*L*d + L**2))/(4*(M*L**2 + 3*m*d**2))` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)
- `gen-20261125-0224-016` [interesting] Two-stage Atwood machine with a massive pulley: `h*m_2*(4*m_1 + M)/(R*m_1*(2*m_1 + 2*m_2 + M))` (gemini:gemini-4-hydrogen / gemini:gemini-3-flash-preview)

## Rejected

- `gen-20261125-0224-008` [author] Disk accelerated by a string tension — incomplete record: missing ['solution_profile']
- `gen-20261125-0224-009` [precheck] Rod pivoted at one end, torque from a perpendicular force — ValueError: reserved identifier 'I'
