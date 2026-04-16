/**
 * REST API for skill management.
 */
import { getAllSkills, getSkill, getCustomSkills, addCustomSkill, updateCustomSkill, deleteCustomSkill } from '../../skills/registry.js'
import { executeSkill } from '../../skills/executor.js'

export function registerSkillRoutes(router: Map<string, (req: Request) => Promise<Response>>) {
  router.set('GET:/api/skills', async () => {
    const builtin = getAllSkills().map((s) => ({
      name: s.name,
      description: s.description,
      triggers: s.triggers || [],
      enabled: s.enabled,
      isDefault: true,
    }))
    const custom = getCustomSkills().map((s) => ({
      name: s.name,
      description: s.description,
      triggers: s.triggers || [],
      enabled: s.enabled,
      isDefault: false,
    }))
    const skills = [...builtin, ...custom]
    return Response.json({ skills, count: skills.length })
  })

  router.set('POST:/api/skills/execute', async (req: Request) => {
    try {
      const body = (await req.json()) as {
        name?: string
        args?: string
        systemPrompt?: string
      }

      if (!body.name) {
        return Response.json({ error: 'name is required' }, { status: 400 })
      }

      const result = executeSkill(body.name, body.args, {
        systemPrompt: body.systemPrompt || '',
      })

      if (!result.success) {
        return Response.json({ error: result.error }, { status: 404 })
      }

      return Response.json({
        skillName: result.skillName,
        systemPrompt: result.systemPrompt,
        success: true,
      })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 500 })
    }
  })

  router.set('POST:/api/skills', async (req: Request) => {
    try {
      const body = (await req.json()) as SkillDef
      if (!body.name || !body.prompt) {
        return Response.json({ error: 'name and prompt are required' }, { status: 400 })
      }
      addCustomSkill({ ...body, isDefault: false })
      return Response.json({ ok: true, skill: body })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 500 })
    }
  })

  router.set('PUT:/api/skills/:name', async (req: Request) => {
    try {
      const url = new URL(req.url)
      const name = url.searchParams.get('name')
      if (!name) return Response.json({ error: 'name is required' }, { status: 400 })
      const existing = getCustomSkills().find((s) => s.name === name)
      if (!existing) return Response.json({ error: 'skill not found or is default' }, { status: 404 })
      const updates = await req.json() as Partial<SkillDef>
      updateCustomSkill(name, updates)
      return Response.json({ ok: true })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 500 })
    }
  })

  router.set('POST:/api/skills/:name/duplicate', async (req: Request) => {
    try {
      const url = new URL(req.url)
      const name = url.searchParams.get('name')
      if (!name) return Response.json({ error: 'name is required' }, { status: 400 })
      const skill = getAllSkills().find((s) => s.name === name) || getCustomSkills().find((s) => s.name === name)
      if (!skill) return Response.json({ error: 'skill not found' }, { status: 404 })
      const copyName = `${skill.name} (copy)`
      addCustomSkill({ ...skill, name: copyName, isDefault: false })
      return Response.json({ ok: true, name: copyName })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 500 })
    }
  })

  router.set('DELETE:/api/skills/:name', async (req: Request) => {
    try {
      const url = new URL(req.url)
      const name = url.searchParams.get('name')
      if (!name) return Response.json({ error: 'name is required' }, { status: 400 })
      const isDefault = getAllSkills().some((s) => s.name === name)
      if (isDefault) return Response.json({ error: 'cannot delete default skill' }, { status: 403 })
      const deleted = deleteCustomSkill(name)
      if (!deleted) return Response.json({ error: 'skill not found' }, { status: 404 })
      return Response.json({ ok: true })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 500 })
    }
  })

  router.set('PATCH:/api/skills/:name/enable', async (req: Request) => {
    try {
      const url = new URL(req.url)
      const name = url.searchParams.get('name')
      const enabled = url.searchParams.get('enabled')
      if (!name) return Response.json({ error: 'name is required' }, { status: 400 })
      if (enabled === null) return Response.json({ error: 'enabled is required' }, { status: 400 })
      const isEnabled = enabled === 'true'
      const updated = updateCustomSkill(name, { enabled: isEnabled })
      if (!updated) return Response.json({ error: 'skill not found' }, { status: 404 })
      return Response.json({ ok: true, enabled: isEnabled })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 500 })
    }
  })
}

interface SkillDef {
  name: string
  description: string
  prompt: string
  triggers?: string[]
  enabled: boolean
  isDefault?: boolean
}
