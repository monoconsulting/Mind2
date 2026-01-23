• Findings
                                                                                                                                                         
  - Codex CLI itself is installed and logged in (codex-cli 0.87.0, codex login status OK), but both MCP servers were failing with timed out handshaking  
    with MCP server after 10s because npx … startup regularly exceeded Codex’s handshake window.                                                         
  - Codex MCP servers are configured under ~/.codex/config.toml via [mcp_servers.<name>] command/args, or managed with codex mcp add/remove.             
    citeturn0open0turn0open1                                                                                                                         
                                                                                                                                                         

  What I changed (restores functionality)                                                                                                                
                                                                                                                                                         
  - Installed fast local MCP binaries: npm install -g @playwright/mcp@latest figma-developer-mcp@latest.                                                 
  - Re-created both MCP entries using those binaries (no npx): codex mcp add playwright -- mcp-server-playwright and codex mcp add figma -- figma-       
    developer-mcp --stdio (preserved your existing FIGMA_* env config).                                                                                  
  - Config locations: C:\Users\matti\.codex\config.toml:20 (playwright) and C:\Users\matti\.codex\config.toml:23 (figma).                                
  - Validation: Playwright MCP starts and responds (I successfully called its browser_tabs tool); Figma MCP starts and responds (no more 10s handshake   
    timeout).                                                                                                                                            
                                                                                                                                                         

  Plan to restore again if it breaks                                                                                                                     
                                                                                                                                                         
  - Verify Codex: codex --version, codex login status, codex mcp list.                                                                                   
  - If MCP handshake timeouts return: avoid npx in MCP configs; install/update global binaries (npm i -g @playwright/mcp@latest figma-developer-         
    mcp@latest) and re-add servers with codex mcp remove … / codex mcp add …. (Playwright MCP is commonly run via npx @playwright/mcp@latest, but npx can    be too slow on Windows for Codex’s handshake.) citeturn0open2
  - If only Figma calls fail after startup: rotate/replace the Figma token and re-run codex mcp list to confirm env is set.                              

 