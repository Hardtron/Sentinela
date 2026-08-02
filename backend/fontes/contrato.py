"""Tipos comuns; nenhum provedor escreve diretamente em regra de alerta."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


class ConfiguracaoAusente(ValueError):
    """A fonte é conhecida, mas falta configuração explícita para consultá-la."""


class ContratoInvalido(ValueError):
    """A resposta não satisfaz o contrato documentado do provedor."""


@dataclass(frozen=True)
class Requisicao:
    provedor: str
    conjunto: str
    url: str
    parametros: Dict[str, str] = field(default_factory=dict)
    cabecalhos: Dict[str, str] = field(default_factory=dict, repr=False)
    metodo: str = "GET"
    corpo: Optional[bytes] = field(default=None, repr=False)
    metadados: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Resposta:
    url_publica: str
    status: int
    tipo_conteudo: str
    dados: bytes
    etag: Optional[str] = None
    ultima_modificacao: Optional[str] = None


@dataclass(frozen=True)
class Estacao:
    provedor: str
    codigo: str
    nome: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_m: Optional[float] = None
    metadados: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Observacao:
    estacao_codigo: str
    medido_em: datetime
    variavel: str
    valor: float
    unidade: str
    periodo_s: Optional[int] = None
    qualificacao: Optional[str] = None
    revisao: str = "ORIGINAL"
    metadados: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Feicao:
    identificador: str
    geometria: Optional[Dict[str, Any]]
    propriedades: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConteudoNormalizado:
    estacoes: List[Estacao] = field(default_factory=list)
    observacoes: List[Observacao] = field(default_factory=list)
    feicoes: List[Feicao] = field(default_factory=list)
    metadados: Dict[str, Any] = field(default_factory=dict)
