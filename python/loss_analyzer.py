"""
Loss Analyzer & Adaptive Learning System
─────────────────────────────────────────
TRUE adaptive learning - the bot analyzes WHY it lost and creates new rules.

Example:
  Trade: BUY because "FVG detected"
  Result: LOSS (-50 pips)
  
  Bot analyzes:
    - Re-scans price action that happened
    - Finds: "There was a BIGGER bearish FVG below that I missed"
    - Lesson: "Always check for opposing FVGs before entry"
    - Creates Rule: "If opposing FVG is larger, BLOCK the trade"
  
  Next time:
    - Signal: BUY (FVG setup)
    - Bot checks: Opposing FVG found below (larger)
    - Decision: BLOCK TRADE (rule #1)
    - Result: Avoided another -50 pip loss
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import Counter
import json

logger = logging.getLogger("LOSS_ANALYZER")


@dataclass
class LossLesson:
    """What the bot learned from a losing trade"""
    trade_id: int
    symbol: str
    expected_direction: str  # What we thought
    actual_direction: str     # What happened
    
    # What we saw (why we entered)
    entry_reasons: List[str]
    entry_setups_detected: List[str]
    entry_confidence: float
    
    # What we MISSED (why we lost)
    missed_opposing_signals: List[str]
    strongest_opposing_setup: Optional[str]
    opposing_confluence_count: int
    
    # The lesson
    lesson_summary: str
    new_rule_created: Optional[str]
    setup_to_avoid: Optional[str]
    
    # Context
    htf_bias: str
    kill_zone: str
    spread_pips: float
    timestamp: datetime
    
    # Metadata
    effectiveness_score: float = 0.0  # How useful was this lesson?
    times_prevented_loss: int = 0


@dataclass
class AdaptiveRule:
    """A trading rule created from lessons learned"""
    rule_id: int
    created_at: datetime
    lesson_trade_id: int
    
    rule_type: str  # AVOIDANCE, REQUIREMENT, FILTER
    affected_setup: str  # Which setup does this apply to
    
    # What to check
    check_for: str  # What pattern to look for
    check_direction: str  # BUY or SELL
    threshold: float  # Minimum strength needed
    
    # Description
    description: str
    example: str
    
    # Performance
    active: bool = True
    times_triggered: int = 0
    trades_blocked: int = 0
    estimated_losses_prevented: float = 0.0
    
    # Auto-disable if proven ineffective
    false_positives: int = 0
    last_triggered: Optional[datetime] = None


class LossAnalyzer:
    def __init__(self, mt5_connector, strategy, memory_db, config):
        self.mt5 = mt5_connector
        self.strategy = strategy
        self.memory = memory_db
        self.cfg = config
        
        # Track learned patterns
        self.learned_lessons: List[LossLesson] = []
        self.adaptive_rules: List[AdaptiveRule] = []
        self.pattern_counter: Counter = Counter()
        self.setup_blacklist: Dict[str, datetime] = {}
        
        # Performance tracking
        self.total_losses_analyzed: int = 0
        self.rules_created: int = 0
        self.trades_blocked: int = 0
        
        logger.info("🧠 Adaptive Learning System initialized")
    
    async def analyze_loss(self, trade_record, candles_h4, candles_m15, candles_m5) -> LossLesson:
        """
        Deep analysis of WHY a trade lost.
        Called automatically when a trade closes at SL.
        
        Process:
        1. Fetch price data that happened after entry
        2. Re-scan for patterns in OPPOSITE direction
        3. Compare what we saw vs what we missed
        4. Create lesson and adaptive rule
        5. Store in memory for future use
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 ANALYZING LOSS #{trade_record.ticket}: {trade_record.symbol} {trade_record.direction}")
        logger.info(f"{'='*80}")
        
        symbol = trade_record.symbol
        direction = trade_record.direction
        entry_time = trade_record.open_time
        
        self.total_losses_analyzed += 1
        
        # Step 1: Re-scan for patterns in OPPOSITE direction
        opposite_dir = "SELL" if direction == "BUY" else "BUY"
        
        logger.info(f"📊 Re-scanning market for {opposite_dir} signals we missed...")
        
        missed_signals = self._find_opposing_signals(
            symbol, candles_h4, candles_m15, candles_m5, opposite_dir
        )
        
        # Step 2: Analyze what we saw vs what we missed
        entry_reasons = self._extract_entry_reasons(trade_record)
        entry_setups = self._extract_entry_setups(trade_record)
        
        missed_list = []
        strongest_opposing = None
        opposing_count = 0
        
        # Check each type of opposing signal
        if missed_signals['fvg']:
            missed_list.append(f"Opposing FVG (x{len(missed_signals['fvg'])})")
            opposing_count += len(missed_signals['fvg'])
            if not strongest_opposing:
                strongest_opposing = "FVG"
        
        if missed_signals['stop_hunt']:
            missed_list.append("Stop Hunt in opposite direction")
            opposing_count += 1
            if not strongest_opposing or opposing_count == 1:
                strongest_opposing = "STOP_HUNT"
        
        if missed_signals['order_block']:
            missed_list.append("Order Block opposite direction")
            opposing_count += 1
            if not strongest_opposing:
                strongest_opposing = "ORDER_BLOCK"
        
        if missed_signals['displacement']:
            missed_list.append("Strong displacement opposite direction")
            opposing_count += 1
            strongest_opposing = "DISPLACEMENT"  # This is usually strongest
        
        if missed_signals['structure_break']:
            missed_list.append("HTF structure break opposite direction")
            opposing_count += 1
            strongest_opposing = "STRUCTURE_BREAK"
        
        if missed_signals['liquidity_sweep']:
            missed_list.append("Liquidity sweep opposite direction")
            opposing_count += 1
        
        # Step 3: Generate lesson
        lesson_text = self._create_lesson_text(
            direction, entry_reasons, missed_list, strongest_opposing
        )
        
        new_rule_description = None
        setup_to_avoid = None
        
        # If we missed >= 2 opposing signals, create a new rule
        if opposing_count >= 2:
            new_rule_description = self._create_new_rule_description(
                entry_setups[0] if entry_setups else "UNKNOWN",
                strongest_opposing,
                opposing_count
            )
            
            # Create the actual rule
            self._create_adaptive_rule(
                entry_setups[0] if entry_setups else "UNKNOWN",
                strongest_opposing,
                opposing_count,
                new_rule_description,
                trade_record.ticket
            )
            
            self.rules_created += 1
        
        # If we keep losing on same setup, blacklist it temporarily
        if opposing_count >= 3:
            setup_to_avoid = entry_setups[0] if entry_setups else None
            if setup_to_avoid:
                self.setup_blacklist[setup_to_avoid] = datetime.utcnow() + timedelta(hours=24)
                logger.warning(f"⛔ Temporarily BLACKLISTED setup '{setup_to_avoid}' for 24 hours")
        
        # Step 4: Create lesson object
        lesson = LossLesson(
            trade_id=trade_record.ticket,
            symbol=symbol,
            expected_direction=direction,
            actual_direction=opposite_dir,
            entry_reasons=entry_reasons,
            entry_setups_detected=entry_setups,
            entry_confidence=0.75,  # Default, extract from trade_record if available
            missed_opposing_signals=missed_list,
            strongest_opposing_setup=strongest_opposing,
            opposing_confluence_count=opposing_count,
            lesson_summary=lesson_text,
            new_rule_created=new_rule_description,
            setup_to_avoid=setup_to_avoid,
            htf_bias=getattr(trade_record, 'htf_bias', 'UNKNOWN'),
            kill_zone=getattr(trade_record, 'kill_zone', 'UNKNOWN'),
            spread_pips=0.0,
            timestamp=datetime.utcnow()
        )
        
        # Step 5: Store lesson
        self.learned_lessons.append(lesson)
        self._save_lesson_to_memory(lesson)
        
        # Step 6: Log the lesson
        logger.info(f"\n📝 LESSON LEARNED:")
        logger.info(f"   {lesson.lesson_summary}")
        if lesson.new_rule_created:
            logger.info(f"   ✅ NEW RULE CREATED: {lesson.new_rule_created}")
        if lesson.setup_to_avoid:
            logger.info(f"   ⛔ SETUP BLACKLISTED: {lesson.setup_to_avoid} (24h)")
        logger.info(f"{'='*80}\n")
        
        return lesson
    
    def _find_opposing_signals(self, symbol, candles_h4, candles_m15, candles_m5, opposite_direction) -> Dict:
        """
        Re-run ALL strategy detection in the OPPOSITE direction.
        Find what we MISSED that would have told us NOT to enter.
        """
        opposing_signals = {
            'fvg': [],
            'stop_hunt': None,
            'turtle_soup': None,
            'order_block': None,
            'displacement': False,
            'structure_break': False,
            'liquidity_sweep': False,
        }
        
        # Check for opposing FVGs
        try:
            fvgs = self.strategy.find_fvg(candles_m15)
            for fvg in fvgs:
                if hasattr(fvg, 'direction') and fvg.direction.value == opposite_direction:
                    opposing_signals['fvg'].append(fvg)
        except Exception as e:
            logger.debug(f"FVG check failed: {e}")
        
        # Check for opposing stop hunt
        try:
            if opposite_direction == "SELL":
                sh_signal = self.strategy.stop_hunt_signal(candles_m15, symbol, "BEARISH")
            else:
                sh_signal = self.strategy.stop_hunt_signal(candles_m15, symbol, "BULLISH")
            if sh_signal:
                opposing_signals['stop_hunt'] = sh_signal
        except Exception as e:
            logger.debug(f"Stop hunt check failed: {e}")
        
        # Check for opposing order block
        try:
            obs = self.strategy.find_order_blocks(candles_m15, opposite_direction)
            if obs:
                opposing_signals['order_block'] = obs[0]
        except Exception as e:
            logger.debug(f"Order block check failed: {e}")
        
        # Check for displacement
        opposing_signals['displacement'] = self._check_displacement(candles_m5, opposite_direction)
        
        # Check for structure break
        opposing_signals['structure_break'] = self._check_structure_break(candles_h4, opposite_direction)
        
        # Check for liquidity sweep
        opposing_signals['liquidity_sweep'] = self._check_liquidity_sweep(candles_m15, opposite_direction)
        
        return opposing_signals
    
    def _check_displacement(self, candles_m5, direction) -> bool:
        """Check if there was strong displacement in opposite direction"""
        if len(candles_m5) < 10:
            return False
        
        recent = candles_m5[-10:]
        
        if direction == "SELL":
            bearish_candles = sum(1 for c in recent if c['close'] < c['open'])
            if bearish_candles >= 7:
                return True
        else:
            bullish_candles = sum(1 for c in recent if c['close'] > c['open'])
            if bullish_candles >= 7:
                return True
        
        return False
    
    def _check_structure_break(self, candles_h4, direction) -> bool:
        """Check if H4 structure broke in opposite direction"""
        if len(candles_h4) < 20:
            return False
        
        recent = candles_h4[-20:]
        
        if direction == "SELL":
            swing_high = max(c['high'] for c in recent[:-5])
            return any(c['close'] < swing_high * 0.995 for c in recent[-5:])
        else:
            swing_low = min(c['low'] for c in recent[:-5])
            return any(c['close'] > swing_low * 1.005 for c in recent[-5:])
    
    def _check_liquidity_sweep(self, candles_m15, direction) -> bool:
        """Check for liquidity sweep opposite direction"""
        if len(candles_m15) < 20:
            return False
        
        recent = candles_m15[-20:]
        
        if direction == "SELL":
            # Check for sweep of highs then reversal down
            highs = [c['high'] for c in recent[:-2]]
            if not highs:
                return False
            recent_high = max(highs)
            
            # Did we sweep it with wick then close below?
            for c in recent[-2:]:
                if c['high'] > recent_high and c['close'] < recent_high * 0.998:
                    return True
        else:
            # Check for sweep of lows then reversal up
            lows = [c['low'] for c in recent[:-2]]
            if not lows:
                return False
            recent_low = min(lows)
            
            for c in recent[-2:]:
                if c['low'] < recent_low and c['close'] > recent_low * 1.002:
                    return True
        
        return False
    
    def _extract_entry_reasons(self, trade_record) -> List[str]:
        """Extract why we entered the trade"""
        reasons = []
        
        if hasattr(trade_record, 'reason') and trade_record.reason:
            # Parse the reason string
            reason_text = trade_record.reason
            if "FVG" in reason_text:
                reasons.append("FVG detected")
            if "bullish" in reason_text.lower():
                reasons.append("Bullish HTF bias")
            if "bearish" in reason_text.lower():
                reasons.append("Bearish HTF bias")
            if "stop hunt" in reason_text.lower():
                reasons.append("Stop hunt setup")
        
        if hasattr(trade_record, 'setup_type') and trade_record.setup_type:
            reasons.append(f"{trade_record.setup_type} setup")
        
        return reasons if reasons else ["Unknown reason"]
    
    def _extract_entry_setups(self, trade_record) -> List[str]:
        """Extract which setups were detected"""
        if hasattr(trade_record, 'setup_type') and trade_record.setup_type:
            return [trade_record.setup_type]
        return ["UNKNOWN"]
    
    def _create_lesson_text(self, direction, entry_reasons, missed, strongest) -> str:
        """Create human-readable lesson"""
        text = f"Entered {direction} because: {', '.join(entry_reasons)}. "
        
        if missed:
            text += f"BUT MISSED {len(missed)} opposing signals: {', '.join(missed)}. "
        else:
            text += "No clear opposing signals detected. "
        
        if strongest:
            text += f"Strongest opposing force was: {strongest}. "
        
        text += "💡 LESSON: Always scan for opposing confluence before entry. "
        text += "If 2+ opposing signals exist, SKIP the trade."
        
        return text
    
    def _create_new_rule_description(self, setup_type, opposing_type, opposing_count) -> str:
        """Create description for new adaptive rule"""
        return (
            f"Before entering {setup_type}, check for {opposing_type} in opposite direction. "
            f"If {opposing_count}+ opposing signals exist, BLOCK the trade."
        )
    
    def _create_adaptive_rule(self, setup_type, opposing_setup, threshold, description, trade_id):
        """Create a new trading rule that will be checked before future entries"""
        rule = AdaptiveRule(
            rule_id=len(self.adaptive_rules) + 1,
            created_at=datetime.utcnow(),
            lesson_trade_id=trade_id,
            rule_type="AVOIDANCE",
            affected_setup=setup_type,
            check_for=opposing_setup,
            check_direction="OPPOSITE",
            threshold=float(threshold),
            description=description,
            example=f"Example: If entering {setup_type} BUY, check for {opposing_setup} SELL signals",
            active=True
        )
        
        self.adaptive_rules.append(rule)
        logger.info(f"✅ Created adaptive rule #{rule.rule_id}: {rule.description}")
    
    def should_block_entry(self, symbol, setup_type, direction, candles_h4, candles_m15, candles_m5) -> Tuple[bool, str]:
        """
        Check if any learned rules say we should AVOID this entry.
        Called BEFORE placing any trade.
        
        Returns: (should_block, reason)
        """
        # Check setup blacklist
        if setup_type in self.setup_blacklist:
            blacklist_until = self.setup_blacklist[setup_type]
            if datetime.utcnow() < blacklist_until:
                return True, f"SETUP_BLACKLISTED (learned pattern - too many losses)"
        
        # Check each adaptive rule
        for rule in self.adaptive_rules:
            if not rule.active:
                continue
            
            if rule.affected_setup != setup_type:
                continue
            
            # This rule applies to this setup
            logger.debug(f"🧠 Checking adaptive rule #{rule.rule_id}: {rule.description}")
            
            # Get opposite direction
            opposite_dir = "SELL" if direction == "BUY" else "BUY"
            
            # Re-scan for opposing signals
            opposing_signals = self._find_opposing_signals(
                symbol, candles_h4, candles_m15, candles_m5, opposite_dir
            )
            
            # Count opposing confluence
            opposing_count = 0
            if opposing_signals['fvg']:
                opposing_count += len(opposing_signals['fvg'])
            if opposing_signals['stop_hunt']:
                opposing_count += 1
            if opposing_signals['order_block']:
                opposing_count += 1
            if opposing_signals['displacement']:
                opposing_count += 2  # Displacement is strong
            if opposing_signals['structure_break']:
                opposing_count += 2  # Structure break is strong
            if opposing_signals['liquidity_sweep']:
                opposing_count += 1
            
            # If opposing confluence meets threshold, block
            if opposing_count >= rule.threshold:
                rule.times_triggered += 1
                rule.trades_blocked += 1
                rule.last_triggered = datetime.utcnow()
                
                self.trades_blocked += 1
                
                block_reason = (
                    f"ADAPTIVE_RULE_#{rule.rule_id}: Found {opposing_count} opposing signals "
                    f"(threshold: {rule.threshold}). Learned from trade #{rule.lesson_trade_id}."
                )
                
                logger.warning(f"🚫 {block_reason}")
                return True, block_reason
        
        return False, "OK"
    
    def _save_lesson_to_memory(self, lesson: LossLesson):
        """Save lesson to SQLite database for persistence"""
        try:
            cursor = self.memory.conn.cursor()
            
            cursor.execute("""
            INSERT OR REPLACE INTO loss_lessons (
                trade_id, symbol, expected_direction, actual_direction,
                entry_reasons, missed_signals, strongest_opposing,
                lesson_summary, new_rule, setup_to_avoid, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lesson.trade_id,
                lesson.symbol,
                lesson.expected_direction,
                lesson.actual_direction,
                json.dumps(lesson.entry_reasons),
                json.dumps(lesson.missed_opposing_signals),
                lesson.strongest_opposing_setup,
                lesson.lesson_summary,
                lesson.new_rule_created,
                lesson.setup_to_avoid,
                lesson.timestamp
            ))
            
            self.memory.conn.commit()
        except Exception as e:
            logger.error(f"Failed to save lesson to memory: {e}")
    
    def get_learning_stats(self) -> Dict:
        """Get stats on what the bot has learned"""
        stats = {
            'total_losses_analyzed': self.total_losses_analyzed,
            'lessons_learned': len(self.learned_lessons),
            'adaptive_rules_created': len(self.adaptive_rules),
            'active_rules': len([r for r in self.adaptive_rules if r.active]),
            'trades_blocked': self.trades_blocked,
            'setups_blacklisted': len(self.setup_blacklist),
            'most_common_miss': None,
            'most_effective_rule': None
        }
        
        # Find most common thing we miss
        all_missed = []
        for lesson in self.learned_lessons:
            all_missed.extend(lesson.missed_opposing_signals)
        
        if all_missed:
            most_common = Counter(all_missed).most_common(1)[0]
            stats['most_common_miss'] = f"{most_common[0]} (missed {most_common[1]} times)"
        
        # Find most effective rule
        if self.adaptive_rules:
            most_effective = max(self.adaptive_rules, key=lambda r: r.trades_blocked)
            if most_effective.trades_blocked > 0:
                stats['most_effective_rule'] = (
                    f"Rule #{most_effective.rule_id}: {most_effective.description} "
                    f"(blocked {most_effective.trades_blocked} trades)"
                )
        
        return stats
