import React, { useState, useEffect, useMemo } from 'react'
import { FiEdit3, FiPlus, FiTrash2, FiSettings, FiMaximize2, FiX, FiSave } from 'react-icons/fi'
import { api } from '../api'

// Modal component for expanded prompt editing
function PromptModal({ isOpen, onClose, prompt, onSave }) {
  const [editedPrompt, setEditedPrompt] = useState(prompt)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    setEditedPrompt(prompt)
  }, [prompt])

  if (!isOpen || !prompt) return null

  const handleSave = async () => {
    if (!editedPrompt) return
    try {
      setIsSaving(true)
      await onSave(editedPrompt)
      onClose()
    } catch (err) {
      // Error handled by parent component
      console.error('Failed to save prompt from modal', err)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 className="text-xl font-semibold text-white">{prompt.title}</h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <FiX className="text-gray-400" />
          </button>
        </div>
        <div className="p-4 flex-1 overflow-auto">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Beskrivning
              </label>
              <textarea
                value={editedPrompt.description || ''}
                onChange={(e) => setEditedPrompt({ ...editedPrompt, description: e.target.value })}
                className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 h-20 resize-none"
                placeholder="Kort beskrivning av vad prompten används till..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Systemprompt
              </label>
              <textarea
                value={editedPrompt.prompt_content || ''}
                onChange={(e) => setEditedPrompt({ ...editedPrompt, prompt_content: e.target.value })}
                className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 h-96 font-mono text-sm resize-none"
                placeholder="Ange systemprompt här..."
              />
            </div>
          </div>
        </div>
        <div className="p-4 border-t border-gray-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={isSaving}
            className={`px-4 py-2 rounded-lg transition-colors ${
              isSaving
                ? 'bg-gray-600 text-gray-300 cursor-not-allowed'
                : 'bg-gray-700 text-white hover:bg-gray-600'
            }`}
          >
            Avbryt
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className={`px-4 py-2 flex items-center gap-2 rounded-lg transition-colors ${
              isSaving
                ? 'bg-red-700/60 text-white cursor-wait'
                : 'bg-red-600 text-white hover:bg-red-700'
            }`}
          >
            <FiSave /> {isSaving ? 'Sparar...' : 'Spara'}
          </button>
        </div>
      </div>
    </div>
  )
}

// Modal for adding/editing providers
function ProviderModal({ isOpen, onClose, provider, onSave, existingProviders }) {
  const [editedProvider, setEditedProvider] = useState(
    provider || {
      provider_name: 'OpenAI',
      own_name: '',
      api_key: '',
      endpoint_url: '',
      enabled: false
    }
  )

  useEffect(() => {
    if (provider) {
      setEditedProvider(provider)
    } else {
      setEditedProvider({
        provider_name: 'OpenAI',
        own_name: '',
        api_key: '',
        endpoint_url: '',
        enabled: false
      })
    }
  }, [provider])

  if (!isOpen) return null

  // Get unique provider types from existing providers
  const providerTypes = [...new Set(existingProviders?.map(p => p.provider_name) || [])].sort()

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-gray-800 rounded-lg max-w-2xl w-full">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 className="text-xl font-semibold text-white">
            {provider ? 'Redigera leverantör' : 'Lägg till leverantör'}
          </h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <FiX className="text-gray-400" />
          </button>
        </div>
        <div className="p-4">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Leverantörstyp
              </label>
              <select
                value={editedProvider.provider_name}
                onChange={(e) => setEditedProvider({ ...editedProvider, provider_name: e.target.value })}
                className="w-full bg-gray-700 text-white rounded-lg px-3 py-2"
              >
                {providerTypes.map((type) => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Eget namn (valfritt)
              </label>
              <input
                type="text"
                value={editedProvider.own_name || ''}
                onChange={(e) => setEditedProvider({ ...editedProvider, own_name: e.target.value })}
                className="w-full bg-gray-700 text-white rounded-lg px-3 py-2"
                placeholder="Min OpenAI-konfiguration..."
              />
            </div>
            {editedProvider.provider_name === 'Ollama' ? (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Endpoint URL
                </label>
                <input
                  type="text"
                  value={editedProvider.endpoint_url || ''}
                  onChange={(e) => setEditedProvider({ ...editedProvider, endpoint_url: e.target.value })}
                  className="w-full bg-gray-700 text-white rounded-lg px-3 py-2"
                  placeholder="http://localhost:11434"
                />
              </div>
            ) : (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  API-nyckel
                </label>
                <input
                  type="password"
                  value={editedProvider.api_key || ''}
                  onChange={(e) => setEditedProvider({ ...editedProvider, api_key: e.target.value })}
                  className="w-full bg-gray-700 text-white rounded-lg px-3 py-2"
                  placeholder="sk-..."
                />
              </div>
            )}
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="enabled"
                checked={editedProvider.enabled}
                onChange={(e) => setEditedProvider({ ...editedProvider, enabled: e.target.checked })}
                className="w-5 h-5 rounded bg-gray-700 border-gray-600 text-red-600 focus:ring-red-500"
              />
              <label htmlFor="enabled" className="text-sm font-medium text-gray-300">
                Aktiverad
              </label>
            </div>
          </div>
        </div>
        <div className="p-4 border-t border-gray-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            Avbryt
          </button>
          <button
            onClick={() => {
              onSave(editedProvider)
              onClose()
            }}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Spara
          </button>
        </div>
      </div>
    </div>
  )
}

// Modal for managing models
function ModelModal({ isOpen, onClose, providerId, models, onSave, onDelete }) {
  const [newModel, setNewModel] = useState('')
  const [modelList, setModelList] = useState(models || [])

  useEffect(() => {
    setModelList(models || [])
  }, [models])

  if (!isOpen) return null

  const handleAddModel = () => {
    if (newModel.trim()) {
      onSave(providerId, { model_name: newModel.trim(), display_name: newModel.trim(), is_active: true })
      setNewModel('')
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-gray-800 rounded-lg max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 className="text-xl font-semibold text-white">Hantera modeller</h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <FiX className="text-gray-400" />
          </button>
        </div>
        <div className="p-4 flex-1 overflow-auto">
          <div className="space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={newModel}
                onChange={(e) => setNewModel(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddModel()}
                className="flex-1 bg-gray-700 text-white rounded-lg px-3 py-2"
                placeholder="Modellnamn (t.ex. gpt-4, claude-3-opus)"
              />
              <button
                onClick={handleAddModel}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
              >
                <FiPlus /> Lägg till
              </button>
            </div>
            <div className="space-y-2">
              {modelList.map((model) => (
                <div key={model.id} className="flex items-center justify-between p-3 bg-gray-700 rounded-lg">
                  <span className="text-white">{model.model_name}</span>
                  <button
                    onClick={() => onDelete(model.id)}
                    className="p-2 hover:bg-gray-600 rounded-lg transition-colors text-red-400"
                  >
                    <FiTrash2 />
                  </button>
                </div>
              ))}
              {modelList.length === 0 && (
                <p className="text-gray-400 text-center py-4">Inga modeller tillagda än</p>
              )}
            </div>
          </div>
        </div>
        <div className="p-4 border-t border-gray-700 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            Stäng
          </button>
        </div>
      </div>
    </div>
  )
}

export default function AiPage() {
  const [activeTab, setActiveTab] = useState('prompts')
  const [modalOpen, setModalOpen] = useState(false)
  const [providerModalOpen, setProviderModalOpen] = useState(false)
  const [modelModalOpen, setModelModalOpen] = useState(false)
  const [selectedPromptId, setSelectedPromptId] = useState(null)
  const [selectedProvider, setSelectedProvider] = useState(null)
  const [selectedProviderId, setSelectedProviderId] = useState(null)
  const [providers, setProviders] = useState([])
  const [systemPrompts, setSystemPrompts] = useState([])
  const [originalPrompts, setOriginalPrompts] = useState([])
  const [unsavedPrompts, setUnsavedPrompts] = useState(() => new Set())
  const [savingPrompts, setSavingPrompts] = useState(() => new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const selectedPrompt = useMemo(
    () => systemPrompts.find((prompt) => prompt.id === selectedPromptId) || null,
    [systemPrompts, selectedPromptId]
  )

  const parseModelId = (value) => {
    if (value === undefined || value === null || value === '') return null
    const parsed = parseInt(value, 10)
    return Number.isNaN(parsed) ? null : parsed
  }

  const normalizePrompt = (prompt) => {
    if (!prompt) return { id: null, title: '', description: '', prompt_content: '', selected_model_id: null }
    return {
      ...prompt,
      prompt_content: prompt.prompt_content || '',
      description: prompt.description || '',
      selected_model_id: parseModelId(prompt.selected_model_id)
    }
  }

  const promptsAreEqual = (a, b) => {
    if (!a || !b) return false
    return (
      (a.prompt_content || '') === (b.prompt_content || '') &&
      (a.description || '') === (b.description || '') &&
      parseModelId(a.selected_model_id) === parseModelId(b.selected_model_id)
    )
  }

  const updatePromptDraft = (promptId, changes) => {
    if (!promptId) return
    setSystemPrompts((prev) => {
      let updatedPrompt = null
      const nextPrompts = prev.map((prompt) => {
        if (prompt.id !== promptId) return prompt
        updatedPrompt = normalizePrompt({ ...prompt, ...changes })
        return updatedPrompt
      })

      if (updatedPrompt) {
        const original = originalPrompts.find((prompt) => prompt.id === promptId)
        setUnsavedPrompts((prevUnsaved) => {
          const next = new Set(prevUnsaved)
          if (original && promptsAreEqual(updatedPrompt, original)) {
            next.delete(promptId)
          } else {
            next.add(promptId)
          }
          return next
        })
      }

      return nextPrompts
    })
    setError(null)
  }

  const revertPromptChanges = (promptId) => {
    const original = originalPrompts.find((prompt) => prompt.id === promptId)
    if (!original) return
    const originalClone = { ...original }
    setSystemPrompts((prev) =>
      prev.map((prompt) => (prompt.id === promptId ? originalClone : prompt))
    )
    setError(null)
    setUnsavedPrompts((prev) => {
      const next = new Set(prev)
      next.delete(promptId)
      return next
    })
  }

  // Fetch providers and prompts on mount
  useEffect(() => {
    fetchProviders()
    fetchPrompts()
  }, [])

  const fetchProviders = async () => {
    try {
      const response = await api.fetch('/ai/api/ai-config/providers')
      if (!response.ok) throw new Error('Failed to fetch providers')
      const data = await response.json()
      setProviders(data.providers || [])
    } catch (err) {
      setError('Kunde inte hämta leverantörer: ' + err.message)
    }
  }

  const fetchPrompts = async () => {
    try {
      const response = await api.fetch('/ai/api/ai-config/prompts')
      if (!response.ok) throw new Error('Failed to fetch prompts')
      const data = await response.json()
      const prompts = (data.prompts || []).map((prompt) => normalizePrompt(prompt))
      setSystemPrompts(prompts)
      setOriginalPrompts(prompts.map((prompt) => ({ ...prompt })))
      setUnsavedPrompts(() => new Set())
      setSavingPrompts(() => new Set())
      setLoading(false)
    } catch (err) {
      setError('Kunde inte hämta systemprompter: ' + err.message)
      setLoading(false)
    }
  }

  const handleProviderSave = async (provider) => {
    try {
      let response
      if (provider.id) {
        // Update existing provider
        response = await api.fetch(`/ai/api/ai-config/providers/${provider.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(provider)
        })
      } else {
        // Create new provider
        response = await api.fetch('/ai/api/ai-config/providers', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(provider)
        })
      }

      if (!response.ok) throw new Error('Failed to save provider')

      fetchProviders() // Refresh the list
      setProviderModalOpen(false)
      setSelectedProvider(null)
    } catch (err) {
      setError('Kunde inte spara leverantör: ' + err.message)
    }
  }

  const handleProviderDelete = async (providerId) => {
    if (!confirm('Är du säker på att du vill ta bort denna leverantör?')) return

    try {
      const response = await api.fetch(`/ai/api/ai-config/providers/${providerId}`, {
        method: 'DELETE'
      })

      if (!response.ok) throw new Error('Failed to delete provider')

      fetchProviders() // Refresh the list
    } catch (err) {
      setError('Kunde inte ta bort leverantör: ' + err.message)
    }
  }

  const handleModelSave = async (providerId, model) => {
    try {
      const response = await api.fetch(`/ai/api/ai-config/providers/${providerId}/models`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(model)
      })

      if (!response.ok) throw new Error('Failed to add model')

      fetchProviders() // Refresh the list
    } catch (err) {
      setError('Kunde inte lägga till modell: ' + err.message)
    }
  }

  const handleModelDelete = async (modelId) => {
    try {
      const response = await api.fetch(`/ai/api/ai-config/models/${modelId}`, {
        method: 'DELETE'
      })

      if (!response.ok) throw new Error('Failed to delete model')

      fetchProviders() // Refresh the list
    } catch (err) {
      setError('Kunde inte ta bort modell: ' + err.message)
    }
  }

  const handlePromptEdit = (prompt) => {
    if (!prompt) return
    setSelectedPromptId(prompt.id)
    setModalOpen(true)
  }

  const handlePromptSave = async (updatedPrompt) => {
    if (!updatedPrompt?.id) return null
    const promptId = updatedPrompt.id
    setSavingPrompts((prev) => {
      const next = new Set(prev)
      next.add(promptId)
      return next
    })

    const payload = normalizePrompt(updatedPrompt)

    try {
      const response = await api.fetch(`/ai/api/ai-config/prompts/${promptId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!response.ok) throw new Error('Failed to save prompt')

      let savedPrompt = payload
      const contentType = response.headers.get('content-type') || ''
      if (contentType.includes('application/json')) {
        try {
          const data = await response.json()
          if (data?.prompt) {
            savedPrompt = normalizePrompt(data.prompt)
          } else if (data?.data) {
            savedPrompt = normalizePrompt(data.data)
          } else if (data && Object.keys(data).length > 0) {
            savedPrompt = normalizePrompt({ ...payload, ...data })
          }
        } catch (jsonError) {
          console.warn('Kunde inte tolka svaret från prompt-sparning', jsonError)
        }
      }

      setSystemPrompts((prev) =>
        prev.map((prompt) => (prompt.id === promptId ? { ...prompt, ...savedPrompt } : prompt))
      )

      setOriginalPrompts((prev) => {
        let found = false
        const updatedOriginals = prev.map((prompt) => {
          if (prompt.id === promptId) {
            found = true
            return { ...prompt, ...savedPrompt }
          }
          return prompt
        })
        if (!found) {
          updatedOriginals.push({ ...savedPrompt })
        }
        return updatedOriginals
      })

      setUnsavedPrompts((prev) => {
        const next = new Set(prev)
        next.delete(promptId)
        return next
      })

      setError(null)
      return savedPrompt
    } catch (err) {
      setError('Kunde inte spara prompt: ' + err.message)
      throw err
    } finally {
      setSavingPrompts((prev) => {
        const next = new Set(prev)
        next.delete(promptId)
        return next
      })
    }
  }

  const savePrompt = async (promptId) => {
    const promptToSave = systemPrompts.find((prompt) => prompt.id === promptId)
    if (!promptToSave) return
    try {
      await handlePromptSave(promptToSave)
    } catch (err) {
      console.error('Kunde inte spara prompt', err)
    }
  }

  const isPromptUnsaved = (promptId) => unsavedPrompts.has(promptId)
  const isPromptSaving = (promptId) => savingPrompts.has(promptId)

  const getAllAvailableModels = () => {
    const models = []
    providers.forEach(provider => {
      if (provider.enabled && provider.models && provider.models.length > 0) {
        provider.models.forEach(model => {
          if (model.is_active) {
            models.push({
              id: model.id,
              label: `${provider.own_name || provider.provider_name}: ${model.model_name}`
            })
          }
        })
      }
    })
    return models
  }

  const openModelModal = (provider) => {
    setSelectedProviderId(provider.id)
    setSelectedProvider(provider)
    setModelModalOpen(true)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Laddar...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Error message */}
      {error && (
        <div className="bg-red-600 bg-opacity-20 border border-red-600 rounded-lg p-3 text-red-400">
          {error}
        </div>
      )}

      {/* Header */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">AI-konfiguration</h3>
            <p className="card-subtitle">Hantera AI-modeller och systemprompter</p>
          </div>
          <FiSettings className="text-xl text-red-400" />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-700">
        <button
          onClick={() => setActiveTab('prompts')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'prompts'
              ? 'text-white border-b-2 border-red-600'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Systemprompter
        </button>
        <button
          onClick={() => setActiveTab('llm')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'llm'
              ? 'text-white border-b-2 border-red-600'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          LLM-konfiguration
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'llm' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h4 className="text-lg font-semibold text-white">AI-leverantörer</h4>
            <button
              onClick={() => {
                setSelectedProvider(null)
                setProviderModalOpen(true)
              }}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
            >
              <FiPlus /> Lägg till leverantör
            </button>
          </div>

          <div className="space-y-4">
            {providers.map((provider) => (
              <div key={provider.id} className="card">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={provider.enabled}
                      onChange={() => handleProviderSave({ ...provider, enabled: !provider.enabled })}
                      className="w-5 h-5 rounded bg-gray-700 border-gray-600 text-red-600 focus:ring-red-500"
                    />
                    <div>
                      <h5 className="text-white font-medium">
                        {provider.own_name || provider.provider_name}
                      </h5>
                      <p className="text-sm text-gray-400">
                        {provider.provider_name} - {provider.models?.length || 0} modeller
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => openModelModal(provider)}
                      className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400"
                      title="Hantera modeller"
                    >
                      <FiSettings />
                    </button>
                    <button
                      onClick={() => {
                        setSelectedProvider(provider)
                        setProviderModalOpen(true)
                      }}
                      className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400"
                      title="Redigera"
                    >
                      <FiEdit3 />
                    </button>
                    <button
                      onClick={() => handleProviderDelete(provider.id)}
                      className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-red-400"
                      title="Ta bort"
                    >
                      <FiTrash2 />
                    </button>
                  </div>
                </div>
                {provider.enabled && provider.models?.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-700">
                    <p className="text-sm text-gray-400 mb-2">Tillgängliga modeller:</p>
                    <div className="flex flex-wrap gap-2">
                      {provider.models.map((model) => (
                        <span
                          key={model.id}
                          className="px-2 py-1 bg-gray-700 rounded text-sm text-gray-300"
                        >
                          {model.model_name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
            {providers.length === 0 && (
              <div className="card text-center py-8">
                <p className="text-gray-400">Inga leverantörer konfigurerade än</p>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'prompts' && (
        <div className="space-y-4">
          {systemPrompts.map((prompt) => (
            <div key={prompt.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h4 className="text-lg font-semibold text-white mb-1">{prompt.title}</h4>
                  <p className="text-sm text-gray-400 mb-3">{prompt.description}</p>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">
                        AI-modell
                      </label>
                      <select
                        value={prompt.selected_model_id ?? ''}
                        onChange={(e) =>
                          updatePromptDraft(prompt.id, {
                            selected_model_id: parseModelId(e.target.value)
                          })
                        }
                        className="bg-gray-700 text-white rounded-lg px-3 py-2 text-sm"
                      >
                        <option value="">Välj modell...</option>
                        {getAllAvailableModels().map((model) => (
                          <option key={model.id} value={model.id}>{model.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">
                        Systemprompt
                      </label>
                      <textarea
                        value={prompt.prompt_content}
                        onChange={(e) => updatePromptDraft(prompt.id, { prompt_content: e.target.value })}
                        className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 h-32 text-sm resize-none"
                        placeholder="Ange systemprompt här..."
                      />
                      {isPromptUnsaved(prompt.id) && (
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                          <span className="text-xs text-amber-400">Osparade ändringar</span>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => revertPromptChanges(prompt.id)}
                              className="px-3 py-1 text-sm bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                            >
                              Ångra
                            </button>
                            <button
                              onClick={() => savePrompt(prompt.id)}
                              disabled={isPromptSaving(prompt.id)}
                              className={`px-3 py-1 text-sm flex items-center gap-2 rounded-lg transition-colors ${
                                isPromptSaving(prompt.id)
                                  ? 'bg-red-700/60 text-white cursor-wait'
                                  : 'bg-red-600 text-white hover:bg-red-700'
                              }`}
                            >
                              <FiSave className="text-xs" />{' '}
                              {isPromptSaving(prompt.id) ? 'Sparar...' : 'Spara'}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => handlePromptEdit(prompt)}
                  className="ml-4 p-2 hover:bg-gray-700 rounded-lg transition-colors"
                  title="Öppna i modal"
                >
                  <FiMaximize2 className="text-gray-400" />
                </button>
              </div>
            </div>
          ))}
          {systemPrompts.length === 0 && (
            <div className="card text-center py-8">
              <p className="text-gray-400">Inga systemprompter konfigurerade än</p>
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      <PromptModal
        isOpen={modalOpen}
        onClose={() => {
          setModalOpen(false)
          setSelectedPromptId(null)
        }}
        prompt={selectedPrompt}
        onSave={handlePromptSave}
      />

      <ProviderModal
        isOpen={providerModalOpen}
        onClose={() => {
          setProviderModalOpen(false)
          setSelectedProvider(null)
        }}
        provider={selectedProvider}
        onSave={handleProviderSave}
        existingProviders={providers}
      />

      <ModelModal
        isOpen={modelModalOpen}
        onClose={() => {
          setModelModalOpen(false)
          setSelectedProviderId(null)
          setSelectedProvider(null)
        }}
        providerId={selectedProviderId}
        models={selectedProvider?.models}
        onSave={handleModelSave}
        onDelete={handleModelDelete}
      />
    </div>
  )
}