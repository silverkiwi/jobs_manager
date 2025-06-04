# Purchase Order System - Modular Architecture

This document explains the modular design of the purchase order system. The system has been refactored from a single large JavaScript file into multiple modules with clear responsibilities.

## Module Structure

The system is organized into the following modules:

1. **purchase_order.js** - Main entry point that coordinates initialization
2. **purchase_order_state.js** - Central state management 
3. **purchase_order_grid.js** - AG Grid initialization and manipulation
4. **purchase_order_metal_types.js** - Metal type fetching and management
5. **purchase_order_ui.js** - UI-related functions
6. **purchase_order_xero.js** - Xero integration
7. **purchase_order_events.js** - Event listeners and handlers
8. **purchase_order_summary.js** - Job summary calculations

## Key Improvements

### 1. Separation of Concerns
Each module has a single responsibility, making the code easier to maintain and understand.

### 2. Centralized State Management
- State is managed centrally through the `getState()` and `updateState()` functions
- Backwards compatibility is maintained for legacy code through window properties

### 3. Improved Initialization Flow
- Clear initialization sequence
- Dependencies are properly managed
- Asynchronous operations are handled with Promises

### 4. Better Error Handling
- Consistent error handling patterns
- Clear user feedback through messages

### 5. Readability and Maintainability
- Functions are smaller and have a single responsibility
- Code is organized logically
- JSDoc comments document function parameters and return values

## Usage

The system initializes when the DOM is loaded:

```javascript
document.addEventListener("DOMContentLoaded", initializeApp);
```

The initialization process:
1. Loads data from DOM elements
2. Fetches metal types from the server
3. Initializes the grid
4. Populates the form with purchase order data
5. Updates the submit button state
6. Initializes the job summary section
7. Sets up event listeners

## Extending the System

To add new functionality:
1. Create a new module if the functionality falls outside existing responsibilities
2. Use the central state management for any new state
3. Add event listeners in the events module
4. Document new functions with JSDoc comments
