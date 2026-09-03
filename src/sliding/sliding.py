from typing import TYPE_CHECKING
from src.sliding.directions import Directions
from src.chemistry.registry import SpeciesRegistry, ReactionsRegistry
from random import choice, random
from src.ui.ui import Button
from src.sliding.move_events import MoveEvent, LineMoveEvent
from functools import reduce
from src.utils.utils import weighted_choice

if TYPE_CHECKING:
    from src.chemistry.species import ChemicalSpecies

def can_react(elem1: "ChemicalSpecies", elem2: "ChemicalSpecies"):
    sorted_tuple = tuple(sorted((elem1, elem2), key=lambda species: species.id))
    if len(sorted_tuple) != 2:
        raise ValueError("Unexpected tuple size in `can_react`")
    return ReactionsRegistry.has(reactants=sorted_tuple)

def get_reaction_result(elem1: "ChemicalSpecies", elem2: "ChemicalSpecies"):
    sorted_tuple = tuple(sorted((elem1, elem2), key=lambda species: species.id))
    if len(sorted_tuple) != 2:
        raise ValueError("Unexpected tuple size in `can_react`")
    return ReactionsRegistry.get(reactants=sorted_tuple)

def process_line(line: list["ChemicalSpecies | None"]) -> tuple[list["ChemicalSpecies | None"], list[LineMoveEvent]]:
    new_line: list["ChemicalSpecies | None"] = [None] * len(line)
    events: list[LineMoveEvent] = []
    target_idx = 0
    just_merged = False 

    for current_idx, tile in enumerate(line):
        if tile is None:
            continue
            
        merged = False

        if target_idx > 0 and not just_merged:
            prev_tile = new_line[target_idx - 1]
            if prev_tile is None:
                raise ValueError("Unexpected empty tile during line processing")
            
            if can_react(prev_tile, tile):
                merged_species = get_reaction_result(prev_tile, tile)
                new_line[target_idx - 1] = merged_species
                
                events.append(LineMoveEvent(
                    from_idx=current_idx,
                    to_idx=target_idx - 1,
                    species=tile,
                    merged=True
                ))
                
                just_merged = True
                merged = True

        if not merged:
            new_line[target_idx] = tile
            events.append(LineMoveEvent(
                from_idx=current_idx,
                to_idx=target_idx,
                species=tile,
                merged=False
            ))
            target_idx += 1
            just_merged = False

    return new_line, events

PROGRESSION_TIERS = [
    # Tier 1: Starters only
    {"min_score": 0,    "tier": 1, "balance_threshold": 16, "balance_chance": 0.85, "allow_compounds": False},
    # Tier 2: Simple compounds begin spawning
    {"min_score": 300,  "tier": 2, "balance_threshold": 13, "balance_chance": 0.75, "allow_compounds": True},
    {"min_score": 1200, "tier": 3, "balance_threshold": 10, "balance_chance": 0.60, "allow_compounds": True},
    {"min_score": 2800, "tier": 4, "balance_threshold": 7,  "balance_chance": 0.45, "allow_compounds": True},
    {"min_score": 4500, "tier": 5, "balance_threshold": 4,  "balance_chance": 0.25, "allow_compounds": True},
]

# Player-facing copy shown in a toast the moment a new tier is reached.
# Keyed by tier number (tier 1 is the starting tier, so it has no "unlock").
TIER_UNLOCK_MESSAGES = {
    2: "Tier 2 unlocked! Compounds start appearing.",
    3: "Tier 3 unlocked! Charges are harder to balance.",
    4: "Tier 4 unlocked! Watch your ion balance closely.",
    5: "Tier 5 unlocked! Maximum difficulty reached.",
}

class BalancingChallenge:
    def __init__(self, pos: tuple[int, int], species: "ChemicalSpecies", coefficients: list[int]):
        self.pos = pos
        self.species = species
        self.target_coefficients = coefficients
        self.user_coefficients = [1] * len(coefficients)

    def cycle_coefficient(self, index: int):
        """Cycles value from 1 -> 4 -> 1."""
        self.user_coefficients[index] = (self.user_coefficients[index] % 4) + 1

    def is_solved(self) -> bool:
        return self.user_coefficients == self.target_coefficients

class GameGrid:
    def __init__(self, grid: list[list["ChemicalSpecies | None"]] | None = None, grid_size: int = 5):
        self.grid_size = grid_size
        self.grid: list[list["ChemicalSpecies | None"]] = (
            grid if grid is not None else [[None] * grid_size for _ in range(grid_size)]
        )
        self._buttons: list[Button] = []
        self.score = 0
        self.score_button: None | Button = None
        self.game_over: int = False
        self.active_challenges: dict[tuple[int, int], BalancingChallenge] = {}
        # Total number of successful merges this session, surfaced on the
        # game-over summary panel.
        self.compounds_formed: int = 0

    def _map_coords(self, line_idx: int, outer_idx: int, direction: Directions) -> tuple[int, int]:
        max_idx = self.grid_size - 1
        if direction == Directions.Left:
            return (line_idx, outer_idx)
        elif direction == Directions.Right:
            return (max_idx - line_idx, outer_idx)
        elif direction == Directions.Up:
            return (outer_idx, line_idx)
        elif direction == Directions.Down:
            return (outer_idx, max_idx - line_idx)
        else:
            raise ValueError(f"Unsupported direction: {direction}")

    def _get_line(self, outer_idx: int, direction: Directions) -> list["ChemicalSpecies | None"]:
        return [
            self.grid[r][c]
            for line_idx in range(self.grid_size)
            for c, r in [self._map_coords(line_idx, outer_idx, direction)]
        ]

    def _set_line(self, outer_idx: int, direction: Directions, line: list["ChemicalSpecies | None"]):
        for line_idx, species in enumerate(line):
            c, r = self._map_coords(line_idx, outer_idx, direction)
            self.grid[r][c] = species

    def swipe(self, direction: Directions) -> list[MoveEvent]:
        grid_events: list[MoveEvent] = []

        # Track movements of active challenges during shifts
        old_challenges = dict(self.active_challenges)
        self.active_challenges.clear()

        for outer_idx in range(self.grid_size):
            original_line = self._get_line(outer_idx, direction)
            new_line, line_events = process_line(original_line)
            self._set_line(outer_idx, direction, new_line)

            for e in line_events:
                from_col, from_row = self._map_coords(e.from_idx, outer_idx, direction)
                to_col, to_row = self._map_coords(e.to_idx, outer_idx, direction)

                # Re-map active challenge position if tile slid
                if (from_col, from_row) in old_challenges:
                    ch = old_challenges.pop((from_col, from_row))
                    ch.pos = (to_col, to_row)
                    self.active_challenges[(to_col, to_row)] = ch

                grid_events.append(MoveEvent(
                    from_pos=(from_col, from_row),
                    to_pos=(to_col, to_row),
                    species=e.species,
                    merged=e.merged
                ))

        self.compounds_formed += sum(1 for e in grid_events if e.merged)
        return grid_events

    def create_element(self, species: "ChemicalSpecies", location: tuple[int, int]):
        self.grid[location[1]][location[0]] = species
        
    def pop(self, coords: tuple[int, int]) -> int:
        """Removes the tile at coords, adds its points to the score, and
        returns the points earned so the caller can show feedback (e.g. a
        floating '+N' popup) without having to re-derive it."""
        species = self.grid[coords[1]][coords[0]]
        points = getattr(species, "points", 10)
        self.score += points
        self.grid[coords[1]][coords[0]] = None
        if coords in self.active_challenges:
            del self.active_challenges[coords]
        return points
        
    def get_current_tier_config(self) -> dict:
        current_config = PROGRESSION_TIERS[0]
        for tier_config in PROGRESSION_TIERS:
            if self.score >= tier_config["min_score"]:
                current_config = tier_config
            else:
                break
        return current_config

    def spawn(self):
        tier_config = self.get_current_tier_config()
        current_tier = tier_config["tier"]
        allow_compounds = tier_config["allow_compounds"]

        # Filter species by unlocked tier and compound spawn settings
        spawnable = [
            x for x in SpeciesRegistry.all() 
            if getattr(x, "can_spawn", False) and getattr(x, "unlock_tier", 1) <= current_tier
            and (allow_compounds or getattr(x, "category", "") != "SALT")
        ]

        anions = [x for x in spawnable if getattr(x, "charge", 0) < 0]
        cations = [x for x in spawnable if getattr(x, "charge", 0) > 0]
        anion_charges: int = reduce(lambda acc, x: acc + getattr(x, "charge", 0), anions, 0)
        cation_charges: int = reduce(lambda acc, x: acc + getattr(x, "charge", 0), cations, 0)

        spawnable_locations = [
            (x, y) for y, arr in enumerate(self.grid)
            for x, _ in enumerate(arr)
            if _ is None
        ]

        spawn_location = choice(spawnable_locations)
        balance_threshold = tier_config["balance_threshold"]
        balance_chance = tier_config["balance_chance"]

        if abs(cation_charges + anion_charges) > balance_threshold and random() <= balance_chance:
            pool = anions if abs(anion_charges) > abs(cation_charges) else cations
            spawn_elem = weighted_choice(pool)
        else:
            spawn_elem = weighted_choice(spawnable)

        self.create_element(spawn_elem, spawn_location)
        return (spawn_location, spawn_elem)

    def register_reaction_challenge(self, pos: tuple[int, int], species: "ChemicalSpecies", target_coeffs: list[int]):
        """Creates a non-blocking balancing requirement for a merged tile."""
        self.active_challenges[pos] = BalancingChallenge(pos, species, target_coeffs)

    def clear_temporary_compounds(self) -> list[tuple[tuple[int, int], int]]:
        """Auto-clears any tile that can't be kept, awarding its points.

        Returns a list of (pos, points_earned) pairs, one per cleared tile,
        so callers (e.g. GridView) can spawn a floating score popup at each
        cleared position instead of guessing the amount.
        """
        cleared: list[tuple[tuple[int, int], int]] = []
        for row_idx, row in enumerate(self.grid):
            for col_idx, species in enumerate(row):
                pos = (col_idx, row_idx)
                # Auto-clear only if no balancing challenge is actively pending
                if species is not None and species.can_keep is False and pos not in self.active_challenges:
                    points: int = getattr(species, "points", 10) 
                    self.score += points
                    self.grid[row_idx][col_idx] = None
                    cleared.append((pos, points))
        return cleared