import { getOcrFeedbackProfile } from '@core/server/repositories/ocrFeedbackRepo'
import { isMongoConfigured } from '@core/server/utils/mongo'

const emptyProfile = {
  totalConfirmations: 0,
  correctedConfirmations: 0,
  pairWins: {},
  positionCorrections: {},
  updatedAt: new Date(0).toISOString(),
}

export default defineEventHandler(async () => {
  if (!isMongoConfigured()) {
    return {
      profile: emptyProfile,
      warning: 'Mongo nao configurado para perfil de feedback OCR.',
    }
  }

  const profile = await getOcrFeedbackProfile()
  return { profile }
})
