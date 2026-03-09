from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    business_sector = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    cnpj_basico = Column(String(8), index=True)
    cnpj_full = Column(String(14), index=True)
    razao_social = Column(String(255))
    nome_fantasia = Column(String(255))
    cnae_fiscal = Column(String(7), index=True)
    cnae_descricao = Column(String(255))
    uf = Column(String(2), index=True)
    municipio_codigo = Column(String(4))
    municipio_nome = Column(String(100), index=True)
    logradouro = Column(String(255))
    numero = Column(String(20))
    complemento = Column(String(255))
    bairro = Column(String(100))
    cep = Column(String(8))
    ddd_1 = Column(String(4))
    telefone_1 = Column(String(15))
    ddd_2 = Column(String(4))
    telefone_2 = Column(String(15))
    email = Column(String(255))
    porte = Column(String(2))
    situacao_cadastral = Column(String(2))


class Cnae(Base):
    __tablename__ = "cnaes"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(7), unique=True, index=True)
    descricao = Column(String(255))


class Municipality(Base):
    __tablename__ = "municipalities"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(4), unique=True, index=True)
    nome = Column(String(100))


class ImportStatus(Base):
    __tablename__ = "import_status"

    id = Column(Integer, primary_key=True, index=True)
    file_type = Column(String(50))
    file_index = Column(Integer)
    status = Column(String(20), default="pending")  # pending, downloading, processing, done, error
    progress = Column(Float, default=0.0)
    records_imported = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    uf_filter = Column(String(2), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
