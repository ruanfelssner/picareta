import { access } from 'node:fs/promises'
import { constants } from 'node:fs'
import { resolve } from 'node:path'
import { spawn } from 'node:child_process'
import { normalizePlate } from '@core/shared/valuation'

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

type RunnerError = Error & { unavailable?: boolean }

const OCR_TIMEOUT_MS = 35000
const PYTHON_SCRIPT_PATH = resolve('server/scripts/plate_ocr.py')
const PYTHON_BINS = process.platform === 'win32'
  ? ['python', 'py', 'python3']
  : ['python3', 'python']

const toRunnerError = (value: unknown) => {
  const base = value instanceof Error ? value : new Error(String(value))
  return base as RunnerError
}

const markUnavailable = (value: unknown) => {
  const error = toRunnerError(value)
  error.unavailable = true
  return error
}

const isUnavailableErrorMessage = (message: string) => {
  const normalized = message.toLowerCase()
  return (
    normalized.includes('not found') ||
    normalized.includes('no such file') ||
    normalized.includes('is not recognized') ||
    normalized.includes('could not be found') ||
    normalized.includes('não foi encontrado') ||
    normalized.includes('nao foi encontrado') ||
    normalized.includes('python nao foi encontrado') ||
    normalized.includes('python nÃ£o foi encontrado')
  )
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

const runPythonOcr = async (
  pythonBin: string,
  scriptPath: string,
  timeoutMs: number,
  imageBase64: string,
) => {
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

    child.stdin.on('error', (error) => {
      const message = String(error?.message || '')
      if (message.includes('EPIPE') || message.includes('EOF')) {
        return
      }
      clearTimeout(timeout)
      finish(() => rejectProcess(error))
    })

    child.on('error', (error) => {
      clearTimeout(timeout)

      const maybeErr = error as NodeJS.ErrnoException
      if (maybeErr?.code === 'ENOENT') {
        finish(() => rejectProcess(markUnavailable(new Error(`Python executable not found: ${pythonBin}`))))
        return
      }

      finish(() => rejectProcess(error))
    })

    child.on('close', (code) => {
      clearTimeout(timeout)
      finish(() => resolveProcess({ code, stdout, stderr }))
    })

    child.on('spawn', () => {
      try {
        child.stdin.end(payload)
      } catch (error) {
        clearTimeout(timeout)
        finish(() => rejectProcess(error))
      }
    })
  })

  const rawOutput = output.stdout.trim()
  let parsed: PythonOcrPayload | null = null
  try {
    parsed = rawOutput ? (JSON.parse(rawOutput) as PythonOcrPayload) : null
  } catch {
    parsed = null
  }

  if (output.code !== 0) {
    const parsedError = String(parsed?.error || '').trim()
    const parsedDetails = String(parsed?.details || '').trim()
    const stderr = output.stderr.trim()
    const primaryMessage = parsedDetails || stderr || rawOutput || parsedError || `Python OCR failed (${pythonBin}).`
    const baseMessage = parsedError && parsedError !== 'ocr_failed' && parsedError !== primaryMessage
      ? `${parsedError}: ${primaryMessage}`
      : primaryMessage

    const isUnavailable = output.code === 9009 || output.code === 127 || isUnavailableErrorMessage(baseMessage)
    if (isUnavailable) {
      throw markUnavailable(new Error(baseMessage))
    }

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

export async function detectPlateFromImageSmart(
  imageBase64: string,
): Promise<OcrResult> {
  await access(PYTHON_SCRIPT_PATH, constants.R_OK)

  let lastError: RunnerError | null = null
  for (const bin of PYTHON_BINS) {
    try {
      return await runPythonOcr(bin, PYTHON_SCRIPT_PATH, OCR_TIMEOUT_MS, imageBase64)
    } catch (error) {
      const runnerError = toRunnerError(error)
      lastError = runnerError

      if (!runnerError.unavailable) {
        throw runnerError
      }
    }
  }

  throw lastError || new Error('Python OCR failed to start.')
}
