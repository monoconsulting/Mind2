# Fix AI System Prompts Editor Functionality

## Context

The AI System Prompts editor (accessible via AI menu → Systemprompter tab, which is the default view when opening the AI menu) has severe usability issues that prevent users from effectively editing prompt content:

### Current Behavior
- **Auto-save on every keystroke:** The textarea in the main view triggers `handlePromptSave()` on every `onChange` event (line 625 in `Ai.jsx`), causing continuous API calls
- **Cursor position loss:** Due to immediate API calls and re-renders, the cursor jumps or loses position while typing
- **Text editing problems:** Users cannot continue writing smoothly, cannot properly select text, and copy/paste operations are disrupted
- **Modal button not functional:** While there's a maximize button (FiMaximize2 icon) to open a modal for larger editing, the underlying issues persist

### Expected Behavior
- Users should be able to type, edit, select, cut, copy, and paste text smoothly without interruptions
- Text cursor should remain stable at the correct position during editing
- A fully functional modal view should be available for expanded editing with proper save/cancel controls
- Changes should only be saved when explicitly requested (e.g., via Save button or Ctrl+S), not on every keystroke

### Business Value / Risk
- **High Priority:** This is a core feature for configuring AI behavior in the system
- **User Frustration:** Current implementation is nearly unusable, preventing proper system configuration
- **Data Integrity Risk:** Continuous auto-save on keystroke may save incomplete or malformed prompts

## Definition of Done

- [ ] Main textarea in Systemprompter tab allows smooth typing without cursor position issues
- [ ] Text selection, cut, copy, and paste operations work correctly in the main textarea
- [ ] Modal opens correctly when clicking the maximize button and provides a larger editing area
- [ ] Modal textarea has full editing functionality (typing, selecting, cut/copy/paste)
- [ ] Save functionality is explicit (button-based or keyboard shortcut), not triggered on every keystroke
- [ ] Auto-save is replaced with debounced save or manual save only
- [ ] Changes are properly tracked and can be discarded (Cancel button in modal)
- [ ] Unit/integration tests verify text editing functionality works correctly
- [ ] Manual testing confirms all editing operations work as expected
- [ ] Performance reviewed - no excessive API calls during editing

## Scope & Constraints

### In Scope:
- Fix textarea onChange behavior to prevent auto-save on every keystroke
- Implement proper state management to maintain cursor position
- Ensure modal editing works correctly with proper save/cancel flow
- Add debounced auto-save (optional) or explicit save button
- Maintain existing functionality for model selection and other fields

### Out of Scope:
- Adding new features beyond the described functionality
- Changing the overall UI/UX design
- Modifying backend API endpoints (unless necessary for the fix)
- Adding rich text editing capabilities

## Technical Notes

**File:** `main-system/app-frontend/src/ui/pages/Ai.jsx`

**Problem Areas:**
- Lines 623-628: textarea with `onChange` handler that immediately calls `handlePromptSave()`
- Lines 412-426: `handlePromptSave()` function makes immediate API call
- Lines 6-72: `PromptModal` component - verify this works correctly after fixing main editor

**Suggested Approach:**
1. Remove auto-save from onChange handler in main textarea
2. Add local state to track unsaved changes
3. Add explicit Save button or implement debounced save (500ms-1000ms delay)
4. Ensure modal properly manages its own state without affecting main view
5. Add keyboard shortcut support (Ctrl+S / Cmd+S) for save action
6. Consider adding visual indicator for unsaved changes

## Links

- Component: [Ai.jsx:623-628](main-system/app-frontend/src/ui/pages/Ai.jsx#L623)
- Modal Component: [Ai.jsx:6-72](main-system/app-frontend/src/ui/pages/Ai.jsx#L6)
- Save Handler: [Ai.jsx:412-426](main-system/app-frontend/src/ui/pages/Ai.jsx#L412)

## Labels

bug, frontend, high-priority, ux, user-experience

## Assignees

@monoconsulting

## Milestone/Project

v1.1 - Core UX Improvements
