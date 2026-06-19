---
name: feedback-clarify-machine-context
description: Al dar comandos, aclarar siempre en qué máquina se corren (PC vs Pi)
metadata:
  type: feedback
---

Al dar instrucciones de consola, indicar **siempre y claramente en qué máquina** se corre cada comando: la **PC Windows (PowerShell)** o la **Raspberry Pi (bash, por SSH)**. Dar los comandos listos para copiar y pegar, con los valores reales ya completados (IP `192.168.1.88`, usuario `ro`, rutas), no con placeholders.

**Why:** En esta sesión corrió un `.ps1` de PowerShell dentro de la terminal de la Pi por error (`-bash: command not found`). Mezclar contextos de máquina es la fuente de confusión más frecuente para ella.

**How to apply:** Encabezar cada bloque con "En tu PC (PowerShell)" o "En la Pi (bash)". Para flujos que saltan entre las dos, sugerir tener dos ventanas abiertas. Ver [[user-rocio]].
