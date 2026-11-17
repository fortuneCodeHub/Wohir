# AI Agent Instructions for Google Adsense BOT

## Project Overview
This is a sophisticated web automation system using a Brain → Connector → Actions → Environment architecture to simulate human-like browsing behavior. The project focuses on automated interactions while maintaining natural patterns.

## Key Architecture Components

### Brain Layer (`Brain/`)
- Core decision-making components in `advanced_brain_box.py`
- Uses `attention_model.py` for human-like behavior simulation
- `decision_mdp.py` implements Markov Decision Process for action selection

### Connector Layer (`Agents/`)
- `agent.py`: Abstract base class defining connector interfaces
- Connectors (like `youtube_connector.py`, `google_connector.py`) implement high-level behaviors
- Bridge between Brain's decisions and atomic Actions

### Actions Layer (`Agents/`)
- Contains atomic operations in `*_actions.py` files
- Each action is a single, focused operation (click, type, scroll, etc.)
- Examples: `navigate_to()`, `search_google()`, `click_element()`

## Development Patterns

### Testing Strategy
- Use `seleniumbase` for integration tests (see `test2.py`)
- Tests inherit from connector classes (e.g., `TestGoogleConnector`)
- Comprehensive logging with `logging_config.logger`
- Error screenshots saved automatically on test failure

### Error Handling
```python
try:
    # Multiple selector attempts pattern
    selectors = [
        "a.primary-selector",
        "div.alternative-selector",
        "[aria-label='Descriptive Label']"
    ]
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                # Process elements
                break
        except Exception:
            continue
except Exception as e:
    logger.error(f"Operation failed: {e}")
    self.save_screenshot("error.png")
```

### Environment Setup
1. Create virtual environment: `python -m venv bot_env`
2. Activate: `source bot_env/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`

## Critical Patterns

### Human-Like Behavior
- Always use brain components for timing/decision making
- Let `AttentionModel` guide engagement patterns
- Implement random delays and natural scrolling

### Selector Strategy
- Use multiple selector attempts for resilience
- Prefer semantic selectors (aria-labels, data-testids)
- Fall back to CSS/XPath when needed

### State Management
- Use `MarkovDecisionProcess` for state transitions
- Track user attention/frustration in `AttentionModel`
- Maintain session context in connector classes

## Integration Points
- Browser automation: Selenium/SeleniumBase
- Decision making: Brain Layer → Connector interface
- Action execution: Connector → Actions → WebDriver

## Common Tasks

### Adding New Behaviors
1. Implement atomic actions in relevant `*_actions.py`
2. Create high-level methods in connector class
3. Update brain decision process to use new actions
4. Add tests in relevant test file

### Debugging
- Check `latest_logs/` for detailed session logs
- Screenshots saved to root on test failures
- Use `logger.debug()` for granular operation tracking