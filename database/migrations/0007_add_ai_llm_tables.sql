-- Migration: Add AI LLM configuration tables
-- Created: 2025-09-27

-- Table for AI LLM providers
CREATE TABLE IF NOT EXISTS ai_llm (
    id INT AUTO_INCREMENT PRIMARY KEY,
    provider_name VARCHAR(100) NOT NULL,  -- OpenAI, Anthropic, Ollama, etc.
    own_name VARCHAR(255),                -- User's custom name for this configuration
    api_key TEXT,                          -- Encrypted API key (NULL for local services like Ollama)
    endpoint_url TEXT,                     -- Custom endpoint URL (for Ollama or self-hosted)
    enabled BOOLEAN DEFAULT false,         -- Whether this provider is active
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table for AI models within each provider
CREATE TABLE IF NOT EXISTS ai_llm_model (
    id INT AUTO_INCREMENT PRIMARY KEY,
    llm_id INT NOT NULL,
    model_name VARCHAR(255) NOT NULL,      -- gpt-4, claude-3, llama2, etc.
    display_name VARCHAR(255),              -- Optional display name
    is_active BOOLEAN DEFAULT true,        -- Whether this model is available for use
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_llm_model (llm_id, model_name),
    FOREIGN KEY (llm_id) REFERENCES ai_llm(id) ON DELETE CASCADE
);

-- Table for system prompts configuration
CREATE TABLE IF NOT EXISTS ai_system_prompts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prompt_key VARCHAR(100) NOT NULL UNIQUE,  -- document_analysis, expense_classification, etc.
    title VARCHAR(255) NOT NULL,
    description TEXT,
    prompt_content TEXT,
    selected_model_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (selected_model_id) REFERENCES ai_llm_model(id) ON DELETE SET NULL
);

-- Insert default system prompts (using INSERT IGNORE for MySQL)
INSERT IGNORE INTO ai_system_prompts (prompt_key, title, description, prompt_content) VALUES
    ('document_analysis', 'Dokumentanalys', 'Analyserar kvitton, fakturor och andra dokument', ''),
    ('expense_classification', 'Utlägg eller företag', 'Avgör om ett kvitto är ett personligt utlägg eller företagskostnad', ''),
    ('receipt_items_classification', 'Klassificering av kvittoposter', 'Kategoriserar och sorterar kvittodata', ''),
    ('accounting', 'Kontering', 'Hanterar all konterings-relaterad information', ''),
    ('first_card', 'First Card', 'Matchar FirstCard-fakturor mot befintliga kvitton', '');

-- Create indexes for better performance
CREATE INDEX idx_ai_llm_enabled ON ai_llm(enabled);
CREATE INDEX idx_ai_llm_model_llm_id ON ai_llm_model(llm_id);
CREATE INDEX idx_ai_llm_model_active ON ai_llm_model(is_active);