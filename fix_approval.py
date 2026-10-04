import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"

# 1. Fix TaskCard.tsx isMine logic
tc_path = os.path.join(base_dir, "mobile/src/components/TaskCard.tsx")
with open(tc_path, "r") as f:
    tc = f.read()

tc = tc.replace(
    "const isMine = item.assigned_to?.id === currentUserId;",
    "const assignedUserId = typeof item.assigned_to === 'string' ? item.assigned_to : item.assigned_to?.id;\n  const isMine = assignedUserId === currentUserId;"
)
with open(tc_path, "w") as f:
    f.write(tc)

# 2. Fix Backend to return 400 instead of 500 for business logic
ts_path = os.path.join(base_dir, "backend/src/services/taskService.ts")
with open(ts_path, "r") as f:
    ts = f.read()

# Instead of throwing, we'll return an object with an error if it's a soft rule
ts = ts.replace(
    "if (task.assigned_to === approverId) throw new Error('No puedes aprobar tu propia foto');",
    "if (task.assigned_to === approverId) throw new Error('NO_PUEDES_APROBAR_PROPIA');"
)
with open(ts_path, "w") as f:
    f.write(ts)

tr_path = os.path.join(base_dir, "backend/src/routes/taskRoutes.ts")
with open(tr_path, "r") as f:
    tr = f.read()

tr = tr.replace(
    """    const result = await taskService.approveTask(req.params.id, req.user.id);
    res.json(result);
  } catch (err: any) { console.error("TASK_ROUTE_ERROR", err); res.status(500).json({ error: err.message }); }""",
    """    const result = await taskService.approveTask(req.params.id, req.user.id);
    res.json(result);
  } catch (err: any) { 
    if (err.message === 'NO_PUEDES_APROBAR_PROPIA') return res.status(400).json({ error: 'No puedes aprobar tu propia foto. Debe hacerlo otro miembro del hogar.' });
    console.error("TASK_ROUTE_ERROR", err); res.status(500).json({ error: err.message }); 
  }"""
)
with open(tr_path, "w") as f:
    f.write(tr)
