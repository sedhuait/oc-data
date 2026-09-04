"""Normalise AMFI's inconsistent section labels into SEBI's standard categories,
and derive asset class and management style. Kept separate so it can be tested
and corrected by PR without touching the importer."""
import re

# canonical SEBI sub-category  <-  the many ways AMFI writes it
SUBCAT = {
  # equity
  "Large Cap Fund": ["large cap fund"],
  "Large & Mid Cap Fund": ["large & mid cap", "large and mid cap"],
  "Mid Cap Fund": ["mid cap fund"],
  "Small Cap Fund": ["small cap fund"],
  "Multi Cap Fund": ["multi cap fund"],
  "Flexi Cap Fund": ["flexi cap fund"],
  "Focused Fund": ["focused fund"],
  "Dividend Yield Fund": ["dividend yield"],
  "Value / Contra Fund": ["value fund", "contra fund", "value/contra"],
  "Sectoral / Thematic": ["sectoral", "thematic"],
  "ELSS": ["elss", "tax saver"],
  "Equity — other": ["equity funds", "equity scheme", "growth"],
  # debt
  "Overnight Fund": ["overnight"],
  "Liquid Fund": ["liquid"],
  "Ultra Short Duration Fund": ["ultra short"],
  "Low Duration Fund": ["low duration"],
  "Money Market Fund": ["money market"],
  "Short Duration Fund": ["short duration", "short term fund"],
  "Medium Duration Fund": ["medium duration", "medium term fund"],
  "Medium to Long Duration Fund": ["medium to long"],
  "Long Duration Fund": ["long duration", "long term fund"],
  "Dynamic Bond": ["dynamic bond", "dynamic term"],
  "Corporate Bond Fund": ["corporate bond"],
  "Credit Risk Fund": ["credit risk"],
  "Banking and PSU Fund": ["banking and psu"],
  "Gilt Fund": ["gilt fund", "gilt"],
  "10-year Constant Maturity Gilt": ["constant maturity"],
  "Floater Fund": ["floater", "floating interest"],
  "Fixed Maturity Plan": ["fixed term plan", "fixed maturity", "interval"],
  "Debt — other": ["income", "debt funds", "debt scheme"],
  # hybrid
  "Aggressive Hybrid Fund": ["aggressive hybrid"],
  "Conservative Hybrid Fund": ["conservative hybrid"],
  "Balanced Hybrid Fund": ["balanced hybrid"],
  "Balanced Advantage / Dynamic Asset Allocation": ["balanced advantage", "dynamic asset allocation"],
  "Multi Asset Allocation": ["multi asset"],
  "Arbitrage Fund": ["arbitrage"],
  "Equity Savings": ["equity savings"],
  "Hybrid — other": ["hybrid fund", "hybrid etf"],
  # passive / other
  "Index Fund": ["index fund"],
  "Equity ETF": ["equity etf"],
  "Debt ETF": ["debt etf"],
  "Gold ETF": ["gold etf"],
  "Silver ETF": ["silver etf"],
  "ETF — other": ["other  etfs", "other etfs", "etfs investing overseas"],
  "Fund of Funds — domestic": ["fof domestic", "fund of funds scheme (domestic)", "fund of funds (domestic)"],
  "Fund of Funds — overseas": ["fof overseas", "fund of funds investing overseas", "overseas fof"],
  "Retirement Fund": ["retirement"],
  "Children's Fund": ["children"],
  "Life Cycle Fund": ["life cycle"],
}
_LOOKUP = [(canon, p) for canon, pats in SUBCAT.items() for p in pats]

ASSET_CLASS = {
  "Equity": ["Large Cap Fund", "Large & Mid Cap Fund", "Mid Cap Fund", "Small Cap Fund", "Multi Cap Fund",
             "Flexi Cap Fund", "Focused Fund", "Dividend Yield Fund", "Value / Contra Fund",
             "Sectoral / Thematic", "ELSS", "Equity — other", "Equity ETF"],
  "Debt": ["Overnight Fund", "Liquid Fund", "Ultra Short Duration Fund", "Low Duration Fund", "Money Market Fund",
           "Short Duration Fund", "Medium Duration Fund", "Medium to Long Duration Fund", "Long Duration Fund",
           "Dynamic Bond", "Corporate Bond Fund", "Credit Risk Fund", "Banking and PSU Fund", "Gilt Fund",
           "10-year Constant Maturity Gilt", "Floater Fund", "Fixed Maturity Plan", "Debt — other", "Debt ETF"],
  "Hybrid": ["Aggressive Hybrid Fund", "Conservative Hybrid Fund", "Balanced Hybrid Fund",
             "Balanced Advantage / Dynamic Asset Allocation", "Multi Asset Allocation", "Arbitrage Fund",
             "Equity Savings", "Hybrid — other"],
  "Commodity": ["Gold ETF", "Silver ETF"],
  "Solution oriented": ["Retirement Fund", "Children's Fund", "Life Cycle Fund"],
  "Other": ["Index Fund", "ETF — other", "Fund of Funds — domestic", "Fund of Funds — overseas"],
}
_ASSET = {sc: a for a, subs in ASSET_CLASS.items() for sc in subs}

PASSIVE_SUB = {"Index Fund", "Equity ETF", "Debt ETF", "Gold ETF", "Silver ETF", "ETF — other"}
PASSIVE_NAME = re.compile(r"\b(index|nifty|sensex|bse\s?\d|etf|exchange traded)\b", re.I)

def sub_category(raw: str, name: str = "") -> str | None:
    s = re.sub(r"\s+", " ", (raw or "").lower()).strip()
    if s:
        for canon, pat in _LOOKUP:
            if pat in s: return canon
    n = (name or "").lower()
    for canon, pat in _LOOKUP:
        if pat in n: return canon
    return None

def asset_class(sub: str | None, name: str = "") -> str | None:
    if sub and sub in _ASSET: return _ASSET[sub]
    n = (name or "").lower()
    if "gold" in n or "silver" in n: return "Commodity"
    return None

def management_style(sub: str | None, name: str = "") -> str:
    """Passive = tracks an index or is an ETF/FoF over one. Everything else is active."""
    if sub in PASSIVE_SUB: return "Passive"
    if sub and sub.startswith("Fund of Funds") and PASSIVE_NAME.search(name or ""): return "Passive"
    if PASSIVE_NAME.search(name or ""): return "Passive"
    return "Active"

def plan_of(raw: str, name: str) -> str | None:
    s = (raw or "").strip().lower()
    if s.startswith("direct"): return "Direct"
    if s.startswith("regular"): return "Regular"
    n = (name or "").lower()
    if "direct" in n: return "Direct"
    if "regular" in n: return "Regular"
    return None

# Theme, for Sectoral/Thematic schemes only. Parsed from the scheme name, which
# always states it. Left empty when the name doesn't say — never guessed.
THEMES = {
  "Banking & financial services": ["banking and financial", "banking & financial", "financial services", "bank fund", "banking fund", "bfsi"],
  "Technology": ["technology", "digital", "\\bit fund", "information tech"],
  "Pharma & healthcare": ["pharma", "healthcare", "health care"],
  "FMCG & consumption": ["consumption", "fmcg", "consumer"],
  "Infrastructure": ["infrastructure", "infra fund"],
  "PSU": ["\\bpsu\\b", "public sector"],
  "Energy": ["energy", "oil", "power", "utilities"],
  "Manufacturing": ["manufacturing", "make in india"],
  "Auto & transport": ["\\bauto\\b", "automobile", "transport", "logistics"],
  "Metals & commodities": ["metal", "mining", "commodit"],
  "Real estate": ["real estate", "reit", "housing"],
  "ESG": ["\\besg\\b", "sustainab", "responsib"],
  "Quant": ["quant"],
  "Business cycle": ["business cycle"],
  "Dividend / value theme": ["special situation", "opportunit"],
  "MNC": ["\\bmnc\\b", "multinational"],
  "Innovation": ["innovation", "new age", "disrupt"],
  "Defence": ["defence", "defense"],
  "Tourism & hospitality": ["tourism", "hospitality", "travel"],
  "International": ["\\bus \\b", "\\busa\\b", "global", "world", "china", "japan", "emerging market", "nasdaq", "s&p 500", "hang seng"],
}
_THEME = [(t, re.compile(p, re.I)) for t, pats in THEMES.items() for p in pats]

def theme(sub: str | None, name: str) -> str | None:
    """Only for thematic/sectoral schemes. Returns None when the name doesn't say."""
    if sub not in ("Sectoral / Thematic", "Equity — other", "ETF — other", "Fund of Funds — overseas"):
        return None
    for t, rx in _THEME:
        if rx.search(name or ""): return t
    return None
