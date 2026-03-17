# 🧠 ADAPTIVE LEARNING ACROSS ACCOUNTS — SOLUTION

## 🎯 The Problem

**Current Behavior:**
```
Account 1 (Demo): Learns 50 lessons → Creates 5 rules
Account 2 (Live): Starts from ZERO lessons → No rules

[You switch to Account 2]
Bot: "I've never seen this before!" ❌
```

**Why?**
```python
# In bot_engine.py line 45-47:
db_path = Path(__file__).parent.parent / "memory" / f"trading_memory_{login}.db"

# Each account gets its own DB:
trading_memory_103143434.db  ← Demo account
trading_memory_567890123.db  ← Live account
```

**The Issue:**
- ❌ Lessons learned on demo don't transfer to live
- ❌ Starting fresh on each new account
- ❌ Wastes all the AI learning

---

## ✅ SOLUTION 1: Shared Global Learning (Recommended)

**Concept:** Keep account-specific trades separate, but share learned lessons & rules globally.

### Architecture:
```
memory/
├── trading_memory_103143434.db  ← Account 1 trades
├── trading_memory_567890123.db  ← Account 2 trades
└── shared_learning.db            ← SHARED lessons & rules (NEW)
```

### Implementation:

#### Step 1: Create Shared Learning DB

**File:** `python/shared_learning.py`

```python
"""
Shared Adaptive Learning Database
───────────────────────────────────
Lessons and rules are shared across ALL accounts.
Trades remain account-specific.
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger("SHARED_LEARNING")


class SharedLearningDB:
    """Global database for lessons & rules shared across accounts"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self._init_database()
    
    def _init_database(self):
        """Create shared learning tables"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.conn.cursor()
        
        # Global learned lessons (from ALL accounts)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS global_lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_account INTEGER,
            symbol TEXT,
            setup_type TEXT,
            opposing_setup TEXT,
            confluence_count INTEGER,
            lesson_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            wins_prevented INTEGER DEFAULT 0,
            applied_count INTEGER DEFAULT 0
        )
        """)
        
        # Global adaptive rules (shared by ALL accounts)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS global_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_type TEXT,
            affected_setup TEXT,
            check_for TEXT,
            check_direction TEXT,
            threshold REAL,
            description TEXT,
            example TEXT,
            status TEXT DEFAULT 'CANDIDATE',
            active INTEGER DEFAULT 0,
            
            -- Performance metrics (aggregated from all accounts)
            total_triggers INTEGER DEFAULT 0,
            total_blocks INTEGER DEFAULT 0,
            losses_prevented REAL DEFAULT 0,
            false_positives INTEGER DEFAULT 0,
            
            -- Quality gates
            sample_size INTEGER DEFAULT 0,
            precision REAL DEFAULT 0.0,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_triggered TIMESTAMP,
            expires_at TIMESTAMP
        )
        """)
        
        # Rule events (track which accounts used which rules)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS global_rule_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id INTEGER,
            account_login INTEGER,
            symbol TEXT,
            event_type TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        self.conn.commit()
        logger.info(f"Shared learning DB initialized: {self.db_path}")
    
    def save_lesson(self, lesson: dict) -> int:
        """Save a lesson from any account to global DB"""
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO global_lessons 
        (source_account, symbol, setup_type, opposing_setup, 
         confluence_count, lesson_summary)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            lesson['account'],
            lesson['symbol'],
            lesson['setup_type'],
            lesson['opposing_setup'],
            lesson['confluence_count'],
            lesson['lesson_summary']
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def save_rule(self, rule: dict) -> int:
        """Save a rule to global DB"""
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO global_rules
        (rule_type, affected_setup, check_for, check_direction,
         threshold, description, example, status, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule['rule_type'],
            rule['affected_setup'],
            rule['check_for'],
            rule['check_direction'],
            rule['threshold'],
            rule['description'],
            rule['example'],
            rule['status'],
            rule['active']
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_active_rules(self) -> List[dict]:
        """Get all active rules (from ALL accounts)"""
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT * FROM global_rules 
        WHERE active = 1 AND status = 'ACTIVE'
        AND (expires_at IS NULL OR expires_at > datetime('now'))
        ORDER BY precision DESC, losses_prevented DESC
        """)
        
        rules = []
        for row in cursor.fetchall():
            rules.append({
                'id': row[0],
                'rule_type': row[1],
                'affected_setup': row[2],
                'check_for': row[3],
                'threshold': row[5],
                'description': row[6],
                'precision': row[14],
                'losses_prevented': row[12]
            })
        
        return rules
    
    def update_rule_performance(self, rule_id: int, blocked: bool, 
                               prevented_loss: bool):
        """Update rule metrics when it triggers"""
        cursor = self.conn.cursor()
        
        if blocked:
            cursor.execute("""
            UPDATE global_rules SET
                total_triggers = total_triggers + 1,
                total_blocks = total_blocks + 1,
                losses_prevented = losses_prevented + ?,
                last_triggered = datetime('now')
            WHERE id = ?
            """, (1.0 if prevented_loss else 0.0, rule_id))
        
        self.conn.commit()
    
    def get_lessons_count(self, setup_type: str, opposing_setup: str) -> int:
        """Count how many times this pattern caused losses (across ALL accounts)"""
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT COUNT(*) FROM global_lessons
        WHERE setup_type = ? AND opposing_setup = ?
        """, (setup_type, opposing_setup))
        
        return cursor.fetchone()[0]
    
    def get_stats(self) -> dict:
        """Get overall shared learning stats"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM global_lessons")
        total_lessons = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM global_rules WHERE active = 1")
        active_rules = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(losses_prevented) FROM global_rules")
        total_prevented = cursor.fetchone()[0] or 0
        
        return {
            'total_lessons': total_lessons,
            'active_rules': active_rules,
            'losses_prevented': int(total_prevented)
        }
```

---

#### Step 2: Update `bot_engine.py`

```python
# At the top with other imports:
from shared_learning import SharedLearningDB

# In __init__() around line 44-48:
def __init__(self, config: dict, news_filter: NewsFilter, shutdown_event: asyncio.Event):
    # ... existing code ...
    
    # Account-specific trade history
    db_path = Path(__file__).parent.parent / "memory" / f"trading_memory_{self.mt5.cfg['login']}.db"
    db_path.parent.mkdir(exist_ok=True)
    self.memory = TradingMemoryDB(db_path)
    
    # NEW: Global shared learning
    shared_db_path = Path(__file__).parent.parent / "memory" / "shared_learning.db"
    self.shared_learning = SharedLearningDB(shared_db_path)
    
    # Pass BOTH databases to brain and analyzer
    self.brain = TradingBrain(self.memory, self.shared_learning, self.cfg)
    self.loss_analyzer = LossAnalyzer(
        self.mt5, 
        self.strategy, 
        self.memory,           # Account-specific trades
        self.shared_learning,  # Global lessons & rules
        self.cfg
    )
```

---

#### Step 3: Update `loss_analyzer.py`

```python
# In __init__():
def __init__(self, mt5_connector, strategy, memory_db, shared_learning_db, config):
    self.mt5 = mt5_connector
    self.strategy = strategy
    self.memory = memory_db             # Account-specific
    self.shared = shared_learning_db    # Global (NEW)
    self.cfg = config
    
    # Load rules from SHARED DB (not account-specific)
    self.adaptive_rules = self.shared.get_active_rules()

# In analyze_loss():
async def analyze_loss(self, trade_record, candles_h4, candles_m15, candles_m5):
    # ... analyze the loss ...
    
    # Save lesson to BOTH databases
    self.memory.save_learned_lesson(lesson)  # Account history
    
    lesson_data = {
        'account': self.mt5.cfg['login'],
        'symbol': lesson.symbol,
        'setup_type': lesson.entry_setups_detected[0],
        'opposing_setup': lesson.strongest_opposing_setup,
        'confluence_count': lesson.opposing_confluence_count,
        'lesson_summary': lesson.lesson_summary
    }
    self.shared.save_lesson(lesson_data)  # GLOBAL (NEW)
    
    # Create rule if needed
    if lesson.opposing_confluence_count >= 3:
        rule_data = {
            'rule_type': 'AVOIDANCE',
            'affected_setup': lesson.entry_setups_detected[0],
            'check_for': lesson.strongest_opposing_setup,
            'check_direction': 'OPPOSITE',
            'threshold': lesson.opposing_confluence_count,
            'description': f"Avoid {lesson.entry_setups_detected[0]} when {lesson.strongest_opposing_setup} detected",
            'example': lesson.lesson_summary[:200],
            'status': 'CANDIDATE',
            'active': 0
        }
        rule_id = self.shared.save_rule(rule_data)  # GLOBAL (NEW)

# In should_block_entry():
def should_block_entry(self, symbol, setup_type, ...):
    # Get rules from SHARED DB (not account-specific)
    active_rules = self.shared.get_active_rules()
    
    for rule in active_rules:
        if self._rule_matches(rule, setup_type, ...):
            # Update GLOBAL rule performance
            self.shared.update_rule_performance(
                rule['id'],
                blocked=True,
                prevented_loss=True  # Assume yes until proven otherwise
            )
            return True, f"SHARED_RULE_{rule['id']}_BLOCKED"
    
    return False, "OK"
```

---

## ✅ SOLUTION 2: Import Lessons from Old Account (Quick Fix)

**If you just want to copy lessons from demo to live once:**

### Create Migration Script:

**File:** `migrate_lessons.py`

```python
"""
Migrate Adaptive Learning Between Accounts
────────────────────────────────────────────
Copies lessons and rules from one account DB to another.
"""

import sqlite3
import shutil
from pathlib import Path

def migrate_learning(source_login: int, target_login: int):
    """Copy lessons and rules from source account to target"""
    
    memory_dir = Path(__file__).parent / "memory"
    source_db = memory_dir / f"trading_memory_{source_login}.db"
    target_db = memory_dir / f"trading_memory_{target_login}.db"
    
    if not source_db.exists():
        print(f"❌ Source DB not found: {source_db}")
        return
    
    if not target_db.exists():
        print(f"❌ Target DB not found: {target_db}")
        return
    
    # Backup target DB first
    backup = target_db.with_suffix('.db.backup')
    shutil.copy(target_db, backup)
    print(f"✅ Backup created: {backup}")
    
    # Connect to both databases
    source_conn = sqlite3.connect(source_db)
    target_conn = sqlite3.connect(target_db)
    
    # Copy learned lessons
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()
    
    source_cursor.execute("SELECT * FROM learned_lessons")
    lessons = source_cursor.fetchall()
    
    for lesson in lessons:
        try:
            target_cursor.execute("""
            INSERT INTO learned_lessons 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, lesson)
        except sqlite3.IntegrityError:
            # Skip if already exists
            pass
    
    target_conn.commit()
    print(f"✅ Copied {len(lessons)} lessons")
    
    # Copy adaptive rules
    source_cursor.execute("SELECT * FROM adaptive_rules")
    rules = source_cursor.fetchall()
    
    for rule in rules:
        try:
            target_cursor.execute("""
            INSERT INTO adaptive_rules
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rule)
        except sqlite3.IntegrityError:
            pass
    
    target_conn.commit()
    print(f"✅ Copied {len(rules)} rules")
    
    # Close connections
    source_conn.close()
    target_conn.close()
    
    print(f"✅ Migration complete!")
    print(f"   From: Account {source_login}")
    print(f"   To:   Account {target_login}")


if __name__ == '__main__':
    # Example: Migrate from demo (103143434) to live (567890123)
    source = 103143434  # Your demo account
    target = 567890123  # Your live account
    
    migrate_learning(source, target)
```

**Run it:**
```bash
python migrate_lessons.py
```

---

## 🎯 WHICH SOLUTION TO USE?

### Use **Solution 1 (Shared Global Learning)** if:
- ✅ You trade multiple accounts regularly
- ✅ You want ALL accounts to benefit from learning
- ✅ You want institutional-grade setup
- ✅ Long-term scalability

**Best for:** Prop firm traders, multiple accounts, long-term use

### Use **Solution 2 (Migration Script)** if:
- ✅ You just switched from demo to live once
- ✅ Quick one-time fix
- ✅ Don't want to change architecture

**Best for:** One-time migration, quick fix

---

## 📊 COMPARISON

| Feature | Current | Solution 1 | Solution 2 |
|---------|---------|------------|------------|
| Lessons per account | ✅ | ✅ | ✅ |
| Shared learning | ❌ | ✅ | Partial |
| Auto-sync | ❌ | ✅ | ❌ |
| Account isolation | ✅ | ✅ | ✅ |
| Setup complexity | Low | Medium | Low |
| Long-term value | Low | High | Medium |

---

## 🚀 MY RECOMMENDATION

**Use Solution 1 (Shared Global Learning).**

**Why?**
- ✅ If you learn on demo, live account benefits immediately
- ✅ If you trade 3 accounts, all 3 learn from each other
- ✅ Lessons compound across ALL your trading
- ✅ Professional institutional approach

**Implementation time:** 1-2 hours

**Expected benefit:** 
- Demo account with 50 lessons → Live starts with 50 lessons ✅
- 3 accounts learning simultaneously → 3x faster learning rate
- Rules tested on multiple accounts → Higher confidence

---

## 📝 IMPLEMENTATION CHECKLIST

### For Solution 1:
- [ ] Create `shared_learning.py`
- [ ] Update `bot_engine.py` (add SharedLearningDB)
- [ ] Update `loss_analyzer.py` (use shared DB for rules)
- [ ] Test on demo account first
- [ ] Verify rules persist across account switches
- [ ] Deploy to live

### For Solution 2:
- [ ] Create `migrate_lessons.py`
- [ ] Update source/target account numbers
- [ ] Run migration script
- [ ] Verify lessons copied
- [ ] Test bot on new account
- [ ] Done

---

**Bottom line:** Your adaptive learning is currently account-siloed. Solution 1 makes it GLOBAL across all your accounts — that's institutional-grade. 🧠
