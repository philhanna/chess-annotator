from annotate.ports.game_repository import GameRepository


# Backward-compatible alias retained while the rest of the codebase
# migrates from ``AnnotationRepository`` to ``GameRepository``.
AnnotationRepository = GameRepository
