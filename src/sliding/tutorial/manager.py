from src.sliding.directions import Directions
from src.sliding.sliding import GameGrid
from src.chemistry.registry import SpeciesRegistry

class SlidingTutorialManager:
    def __init__(self, grid_size: int = 4):
        self.grid_size = grid_size
        self.step = 0
        self.substep = 1
        self.is_completed = False
        
        # Load elements from registry
        self.h_species = SpeciesRegistry.get("H")
        self.o_species = SpeciesRegistry.get("O")
        self.na_species = SpeciesRegistry.get("Na")
        self.cl_species = SpeciesRegistry.get("Cl")

        # Holds a callable step-transition to run once the caller confirms
        # any in-flight animation for the current grid has finished playing.
        self._pending_advance = None

        # Tracks which of the 4 directions the player has tried during the
        # movement-only step (Step 0), so we know when to advance.
        self.movement_directions_seen: set[Directions] = set()

        self.game_grid = GameGrid(grid_size=self.grid_size)
        self.reset_step_0()

    def reset_step_0(self):
        """Step 0: Learn Movement (slide a tile in all 4 directions)."""
        self.step = 0
        self.substep = 1
        self.movement_directions_seen = set()
        self.game_grid = GameGrid(grid_size=self.grid_size)
        center = self.grid_size // 2
        self.game_grid.create_element(self.h_species, (center, center))

    def reset_step_1(self):
        """Step 1: Single reaction (H + H -> H2)."""
        self.step = 1
        self.substep = 1
        self.game_grid = GameGrid(grid_size=self.grid_size)
        self.game_grid.create_element(self.h_species, (0, 0))
        self.game_grid.create_element(self.h_species, (1, 0))

    def reset_step_2(self):
        """Step 2: Compound synthesis (Na + Cl -> NaCl)."""
        self.step = 2
        self.substep = 1
        self.game_grid = GameGrid(grid_size=self.grid_size)
        self.game_grid.create_element(self.na_species, (0, 1))
        self.game_grid.create_element(self.cl_species, (2, 1))

    def reset_step_3(self):
        """Step 3a: Multi-step synthesis start (H + O -> OH)."""
        self.step = 3
        self.substep = 1
        self.game_grid = GameGrid(grid_size=self.grid_size)
        # Place H and O adjacent to each other
        self.game_grid.create_element(self.h_species, (0, 2))
        self.game_grid.create_element(self.o_species, (2, 2))

    def setup_step_3_part2(self):
        """Step 3b: Multi-step synthesis finish (OH + H -> H2O)."""
        self.substep = 2
        # Spawn second Hydrogen adjacent to the newly formed Hydroxide (OH)
        self.game_grid.create_element(self.h_species, (1, 2))

    def handle_swipe(self, direction: Directions):
        """Processes swipes and advances steps on reaction completion."""
        if self.is_completed:
            return []

        if self.step == 0:
            # Movement-only step: every direction is allowed here, and
            # nothing reacts yet — this just teaches that swiping slides
            # every tile on the board toward that edge.
            events = self.game_grid.swipe(direction)
            self.movement_directions_seen.add(direction)

            if len(self.movement_directions_seen) >= 4:
                self._pending_advance = self.reset_step_1

            return events

        # Only permit Left/Right swipes for controlled tutorial steps
        if direction not in (Directions.Left, Directions.Right):
            return []

        events = self.game_grid.swipe(direction)
        has_reacted = any(e.merged for e in events)

        if has_reacted:
            if self.step == 1:
                self._pending_advance = self.reset_step_2
            elif self.step == 2:
                self._pending_advance = self.reset_step_3
            elif self.step == 3:
                if self.substep == 1:
                    self._pending_advance = self.setup_step_3_part2
                else:
                    self._pending_advance = self._complete

        return events

    def _complete(self):
        self.is_completed = True

    def advance_if_pending(self):
        """Performs a deferred step transition, if one is queued.

        Callers should invoke this only once the animation for the swipe
        that triggered the reaction has fully finished playing (i.e. once
        the view is no longer animating), so that the pop/spawn animation
        phase still sees the *old* grid that actually reacted, rather than
        a grid that has already jumped ahead to the next tutorial step.
        """
        if self._pending_advance is not None:
            advance_fn = self._pending_advance
            self._pending_advance = None
            advance_fn()

    def get_instruction_text(self, is_touch: bool = False) -> str:
        action = "Swipe" if is_touch else "Press"
        controls_hint = "" if is_touch else " (WASD / Arrow Keys)"

        if self.step == 0:
            directions_left = ", ".join(
                d.name.upper() for d in Directions if d not in self.movement_directions_seen
            )
            return (
                f"Step 0: {action}{controls_hint} to slide every tile that way! "
                f"Try: {directions_left}"
            )
        elif self.step == 1:
            return f"Step 1: {action} LEFT to react H + H -> H₂!"
        elif self.step == 2:
            return f"Step 2: {action} LEFT to react Na + Cl -> NaCl (Table Salt)!"
        elif self.step == 3:
            if self.substep == 1:
                return f"Step 3a: Multi-Step Chain! {action} LEFT to react H + O -> OH (Hydroxide)."
            return f"Step 3b: {action} LEFT again to react OH + H -> H₂O (Water)!"
        return "Tutorial Complete!"