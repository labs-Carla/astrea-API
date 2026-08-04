import logging


def setup_logging(nivel: int = logging.INFO) -> None:
    """
    Configuracion central de logging para toda la app. Se llama una unica vez
    desde main.py al arrancar. Sin esto, los logger.* de cada modulo (ver
    astro_service.py, interpretation_common.py) no tienen ningun handler
    configurado y su salida es inconsistente entre entornos.
    """
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
