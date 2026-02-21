import { access } from 'node:fs/promises'
import { constants } from 'node:fs'
import { resolve } from 'node:path'
import { spawn } from 'node:child_process'
import { normalizePlate } from '@core/shared/valuation'

type RuntimeOcrConfig = {
  plateOcrEngine?: string
  plateOcrPythonBin?: string
  plateOcrPythonScript?: string
  plateOcrTimeoutMs?: number
}

type OcrResult = {
  plate: string
  candidates: string[]
  bestScore: number
  secondScore: number
  rawText: string
  engine: 'python'
}

type PythonOcrPayload = {
  plate?: string
  candidates?: string[]
  bestScore?: number
  secondScore?: number
  rawText?: string
  error?: string
  details?: string
}

const toFiniteNumber = (value: unknown) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

const normalizeOcrResult = (input: PythonOcrPayload): OcrResult => {
  const candidates = Array.isArray(input.candidates)
    ? input.candidates
      .map((item) => normalizePlate(String(item || '')))
      .filter(Boolean)
    : []

  const normalizedPlate = normalizePlate(String(input.plate || ''))
  const plate = normalizedPlate || candidates[0] || ''
  const uniqueCandidates = [...new Set(plate ? [plate, ...candidates] : candidates)].slice(0, 12)

  return {
    plate,
    candidates: uniqueCandidates,
    bestScore: toFiniteNumber(input.bestScore),
    secondScore: toFiniteNumber(input.secondScore),
    rawText: String(input.rawText || ''),
    engine: 'python',
  }
}

export async function detectPlateFromImageSmart(
  imageBase64: string,
  config: RuntimeOcrConfig = {},
): Promise<OcrResult> {
  const engine = String(config.plateOcrEngine || 'python').toLowerCase()
  if (engine !== 'python') {
    throw new Error(`OCR JavaScript foi removido. Use NUXT_PLATE_OCR_ENGINE=python (valor atual: ${engine}).`)
  }

  const pythonBin = String(config.plateOcrPythonBin || 'python3')
  const scriptPath = resolve(String(config.plateOcrPythonScript || 'server/scripts/plate_ocr.py'))
  const timeoutMs = Math.max(3000, Number(config.plateOcrTimeoutMs) || 15000)

  await access(scriptPath, constants.R_OK)

  const payload = JSON.stringify({ imageBase64 })

  const output = await new Promise<{ code: number | null; stdout: string; stderr: string }>((resolveProcess, rejectProcess) => {
    const child = spawn(pythonBin, [scriptPath], {
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    })

    let stdout = ''
    let stderr = ''
    let finished = false

    const finish = (handler: () => void) => {
      if (finished) return
      finished = true
      handler()
    }

    const timeout = setTimeout(() => {
      finish(() => {
        child.kill('SIGKILL')
        rejectProcess(new Error(`Python OCR timeout (${timeoutMs}ms).`))
      })
    }, timeoutMs)

    child.stdout.setEncoding('utf8')
    child.stderr.setEncoding('utf8')
    child.stdout.on('data', (chunk) => {
      stdout += String(chunk || '')
    })
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk || '')
    })

    child.on('error', (error) => {
      clearTimeout(timeout)
      finish(() => rejectProcess(error))
    })

    child.on('close', (code) => {
      clearTimeout(timeout)
      finish(() => resolveProcess({ code, stdout, stderr }))
    })

    child.stdin.write(payload)
    child.stdin.end()
  })

  const rawOutput = output.stdout.trim()
  let parsed: PythonOcrPayload | null = null
  try {
    parsed = rawOutput ? (JSON.parse(rawOutput) as PythonOcrPayload) : null
  } catch {
    parsed = null
  }

  if (output.code !== 0) {
    const parsedError = parsed?.error || parsed?.details || ''
    const stderr = output.stderr.trim()
    const baseMessage = parsedError || stderr || rawOutput || 'Python OCR failed.'
    throw new Error(baseMessage)
  }

  if (!parsed) {
    throw new Error('Python OCR returned invalid JSON.')
  }

  if (parsed.error) {
    throw new Error(parsed.details ? `${parsed.error}: ${parsed.details}` : parsed.error)
  }

  return normalizeOcrResult(parsed)
}
