# claude-config — configuración portable de Claude Code

Repo **público-compatible**: aquí no hay credenciales ni datos de cliente.
La memoria (que sí los tiene) vive aparte, en `claude-memory`.

Es un *plugin marketplace* de Claude Code. Al instalarlo, cada máquina recibe
los agentes, la skill y el hook, y **se actualiza sola** cuando empujas cambios.

## Qué contiene

```
.claude-plugin/marketplace.json     el marketplace
plugins/hidraulica/                 el plugin
  ├── agents/                       deep-reasoner, fast-worker, verificador
  ├── skills/memoria-calculo/       skill + generar_libro.py
  ├── hooks/hooks.json              declara el PreToolUse
  └── scripts/
      ├── guard_deliverables.py     la guardia de entregables
      └── run_guard.ps1             lanzador portable (busca el Python de la máquina)
CLAUDE.base.md                      cuerpo del CLAUDE.md, común a todas las máquinas
settings/                           plantillas por máquina (NO se instalan solas)
```

## Instalar en una máquina nueva

**1. Clonar los dos repos en el perfil de usuario.** Las rutas tienen que ser
estas, porque `~/claude-config` y `~/claude-memory` es lo que apuntan el
`@import` y `autoMemoryDirectory`:

```powershell
git clone https://github.com/ralvarez1802-svg/claude-config.git "$env:USERPROFILE\claude-config"
git clone https://github.com/ralvarez1802-svg/claude-memory.git "$env:USERPROFILE\claude-memory"
```

**2. Copiar el `settings.json` de esa máquina:**

```powershell
Copy-Item "$env:USERPROFILE\claude-config\settings\settings.casa.json" "$env:USERPROFILE\.claude\settings.json"
Copy-Item "$env:USERPROFILE\claude-config\settings\CLAUDE.casa.md"     "$env:USERPROFILE\.claude\CLAUDE.md"
```

(usa `settings.trabajo.json` / `CLAUDE.trabajo.md` en la del trabajo)

`claude-memory` es privado: el primer `git clone` pedirá autenticación y Git
Credential Manager abrirá el navegador. `claude-config` es público y no pide
nada, que es justo por lo que el plugin se auto-actualiza sin credenciales.

**3. Verificar la tabla de intérpretes** del `CLAUDE.md` que acabas de copiar.
Es lo único que no es portable. Si la máquina es nueva, compruébala en vez de
confiar en ella.

**4. Arrancar Claude Code.** El marketplace se registra y el plugin se instala
solo a partir de `extraKnownMarketplaces` + `enabledPlugins`. Si los agentes no
aparecen, `/reload-plugins`.

## Al migrar desde una configuración suelta

Si esa máquina ya tenía los agentes, la skill y el hook en `~/.claude/`, hay
que **borrar los originales**, o no toman efecto los del plugin:

- `~/.claude/agents/*.md` — un agente de usuario **anula** al del plugin con el
  mismo nombre.
- `~/.claude/skills/memoria-calculo/` — la skill del plugin va con espacio de
  nombres (`/hidraulica:memoria-calculo`), así que si dejas la original te
  quedan las dos y no sabes cuál invocas.
- `~/.claude/hooks/guard_deliverables.py` y su bloque `PreToolUse` en
  `settings.json` — si dejas ambos, **el hook se ejecuta dos veces** por
  comando.

## Cambiar algo

Editas aquí, commit, push. Las demás máquinas lo recogen en su siguiente
actualización en segundo plano. Si tocas el plugin, sube `version` en
`plugins/hidraulica/.claude-plugin/plugin.json`: sin eso, las máquinas que ya
lo tienen no reciben la actualización.

Para probar antes de publicar, sin instalar nada:

```powershell
claude --plugin-dir "$env:USERPROFILE\claude-config\plugins\hidraulica"
claude plugin validate "$env:USERPROFILE\claude-config\plugins\hidraulica"
```
