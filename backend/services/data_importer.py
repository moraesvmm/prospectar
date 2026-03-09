"""
Data Importer Service - Downloads and processes Receita Federal open data.
Files are downloaded from dadosabertos.rfb.gov.br/CNPJ/
"""
import os
import csv
import io
import zipfile
import logging
import asyncio
import tempfile
from pathlib import Path
from typing import Optional

import aiohttp
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.config import RFB_BASE_URL, DATA_DIR
from backend.database import SessionLocal
from backend.models import Company, Cnae, Municipality, ImportStatus

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = DATA_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


# Receita Federal CSV column indexes
# Estabelecimentos columns (0-indexed):
EST_CNPJ_BASICO = 0
EST_CNPJ_ORDEM = 1
EST_CNPJ_DV = 2
EST_MATRIZ_FILIAL = 3
EST_NOME_FANTASIA = 4
EST_SITUACAO_CADASTRAL = 5
EST_DATA_SITUACAO = 6
EST_MOTIVO_SITUACAO = 7
EST_CIDADE_EXTERIOR = 8
EST_PAIS = 9
EST_DATA_INICIO = 10
EST_CNAE_PRINCIPAL = 11
EST_CNAE_SECUNDARIA = 12
EST_TIPO_LOGRADOURO = 13
EST_LOGRADOURO = 14
EST_NUMERO = 15
EST_COMPLEMENTO = 16
EST_BAIRRO = 17
EST_CEP = 18
EST_UF = 19
EST_MUNICIPIO = 20
EST_DDD_1 = 21
EST_TELEFONE_1 = 22
EST_DDD_2 = 23
EST_TELEFONE_2 = 24
EST_DDD_FAX = 25
EST_FAX = 26
EST_EMAIL = 27

# Empresas columns:
EMP_CNPJ_BASICO = 0
EMP_RAZAO_SOCIAL = 1
EMP_NATUREZA_JURIDICA = 2
EMP_QUALIFICACAO_RESPONSAVEL = 3
EMP_CAPITAL_SOCIAL = 4
EMP_PORTE = 5
EMP_ENTE_FEDERATIVO = 6


async def download_file(url: str, dest_path: Path, session: aiohttp.ClientSession) -> bool:
    """Download a file with progress tracking."""
    try:
        async with session.get(url) as response:
            if response.status != 200:
                logger.error(f"Falha ao baixar {url}: status {response.status}")
                return False

            with open(dest_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192 * 16):
                    f.write(chunk)

        logger.info(f"Download completo: {dest_path.name}")
        return True
    except Exception as e:
        logger.error(f"Erro no download de {url}: {e}")
        return False


def process_cnaes_file(zip_path: Path, db: Session) -> int:
    """Process the CNAEs ZIP file and import into database."""
    count = 0
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    text = f.read().decode('latin-1')
                    reader = csv.reader(io.StringIO(text), delimiter=';', quotechar='"')
                    for row in reader:
                        if len(row) >= 2:
                            codigo = row[0].strip().replace('"', '')
                            descricao = row[1].strip().replace('"', '')
                            existing = db.query(Cnae).filter(Cnae.codigo == codigo).first()
                            if not existing:
                                db.add(Cnae(codigo=codigo, descricao=descricao))
                                count += 1
                    db.commit()
    except Exception as e:
        logger.error(f"Erro ao processar CNAEs: {e}")
        db.rollback()
    return count


def process_municipios_file(zip_path: Path, db: Session) -> int:
    """Process the Municipios ZIP file and import into database."""
    count = 0
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    text = f.read().decode('latin-1')
                    reader = csv.reader(io.StringIO(text), delimiter=';', quotechar='"')
                    for row in reader:
                        if len(row) >= 2:
                            codigo = row[0].strip().replace('"', '')
                            nome = row[1].strip().replace('"', '')
                            existing = db.query(Municipality).filter(Municipality.codigo == codigo).first()
                            if not existing:
                                db.add(Municipality(codigo=codigo, nome=nome))
                                count += 1
                    db.commit()
    except Exception as e:
        logger.error(f"Erro ao processar Municípios: {e}")
        db.rollback()
    return count


def process_empresas_file(zip_path: Path, db: Session, cnpjs_needed: set) -> dict:
    """Process an Empresas ZIP file. Only import companies whose CNPJ is in cnpjs_needed."""
    razao_map = {}
    porte_map = {}
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    text = f.read().decode('latin-1')
                    reader = csv.reader(io.StringIO(text), delimiter=';', quotechar='"')
                    for row in reader:
                        if len(row) >= 6:
                            cnpj_basico = row[EMP_CNPJ_BASICO].strip().replace('"', '')
                            if cnpj_basico in cnpjs_needed:
                                razao_map[cnpj_basico] = row[EMP_RAZAO_SOCIAL].strip().replace('"', '')
                                porte_map[cnpj_basico] = row[EMP_PORTE].strip().replace('"', '')
    except Exception as e:
        logger.error(f"Erro ao processar Empresas: {e}")
    return {"razao": razao_map, "porte": porte_map}


def process_estabelecimentos_file(
    zip_path: Path,
    db: Session,
    uf_filter: str,
    municipio_map: dict,
    cnae_map: dict,
    batch_size: int = 5000
) -> tuple:
    """Process an Estabelecimentos ZIP file. Filter by UF and active status."""
    count = 0
    cnpjs_found = set()
    batch = []

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    text = f.read().decode('latin-1')
                    reader = csv.reader(io.StringIO(text), delimiter=';', quotechar='"')
                    for row in reader:
                        if len(row) < 28:
                            continue

                        uf = row[EST_UF].strip().replace('"', '')
                        situacao = row[EST_SITUACAO_CADASTRAL].strip().replace('"', '')

                        # Filter: only active companies in the target state
                        if uf != uf_filter.upper() or situacao != "02":
                            continue

                        cnpj_basico = row[EST_CNPJ_BASICO].strip().replace('"', '')
                        cnpj_ordem = row[EST_CNPJ_ORDEM].strip().replace('"', '')
                        cnpj_dv = row[EST_CNPJ_DV].strip().replace('"', '')
                        cnpj_full = f"{cnpj_basico}{cnpj_ordem}{cnpj_dv}"

                        cnae_fiscal = row[EST_CNAE_PRINCIPAL].strip().replace('"', '')
                        mun_codigo = row[EST_MUNICIPIO].strip().replace('"', '')

                        cnpjs_found.add(cnpj_basico)

                        company = Company(
                            cnpj_basico=cnpj_basico,
                            cnpj_full=cnpj_full,
                            nome_fantasia=row[EST_NOME_FANTASIA].strip().replace('"', '') or None,
                            cnae_fiscal=cnae_fiscal,
                            cnae_descricao=cnae_map.get(cnae_fiscal, ""),
                            uf=uf,
                            municipio_codigo=mun_codigo,
                            municipio_nome=municipio_map.get(mun_codigo, ""),
                            logradouro=f"{row[EST_TIPO_LOGRADOURO].strip().replace(chr(34), '')} {row[EST_LOGRADOURO].strip().replace(chr(34), '')}".strip(),
                            numero=row[EST_NUMERO].strip().replace('"', '') or None,
                            complemento=row[EST_COMPLEMENTO].strip().replace('"', '') or None,
                            bairro=row[EST_BAIRRO].strip().replace('"', '') or None,
                            cep=row[EST_CEP].strip().replace('"', '') or None,
                            ddd_1=row[EST_DDD_1].strip().replace('"', '') or None,
                            telefone_1=row[EST_TELEFONE_1].strip().replace('"', '') or None,
                            ddd_2=row[EST_DDD_2].strip().replace('"', '') or None,
                            telefone_2=row[EST_TELEFONE_2].strip().replace('"', '') or None,
                            email=row[EST_EMAIL].strip().replace('"', '') or None,
                            situacao_cadastral=situacao,
                        )
                        batch.append(company)
                        count += 1

                        if len(batch) >= batch_size:
                            db.bulk_save_objects(batch)
                            db.commit()
                            batch = []

                    if batch:
                        db.bulk_save_objects(batch)
                        db.commit()
                        batch = []

    except Exception as e:
        logger.error(f"Erro ao processar Estabelecimentos: {e}")
        db.rollback()

    return count, cnpjs_found


def update_razao_social(db: Session, razao_map: dict, porte_map: dict, batch_size: int = 1000):
    """Update companies with razao_social and porte from Empresas data."""
    for cnpj_basico, razao in razao_map.items():
        db.query(Company).filter(
            Company.cnpj_basico == cnpj_basico,
            Company.razao_social.is_(None)
        ).update(
            {"razao_social": razao, "porte": porte_map.get(cnpj_basico, "")},
            synchronize_session=False
        )
    db.commit()


async def import_data_for_state(uf: str, file_count: int = 10):
    """
    Main import pipeline for a single state.
    Downloads and processes files from Receita Federal.
    """
    db = SessionLocal()

    try:
        # Update status
        status_record = ImportStatus(
            file_type="full_import",
            file_index=0,
            status="downloading",
            progress=0.0,
            uf_filter=uf
        )
        db.add(status_record)
        db.commit()
        status_id = status_record.id

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=3600),
            connector=aiohttp.TCPConnector(limit=5)
        ) as session:

            # Step 1: Download and process CNAEs
            logger.info("Baixando CNAEs...")
            cnae_path = DOWNLOAD_DIR / "Cnaes.zip"
            if not cnae_path.exists():
                await download_file(f"{RFB_BASE_URL}Cnaes.zip", cnae_path, session)
            cnae_count = process_cnaes_file(cnae_path, db)
            logger.info(f"CNAEs importados: {cnae_count}")

            # Step 2: Download and process Municipios
            logger.info("Baixando Municípios...")
            mun_path = DOWNLOAD_DIR / "Municipios.zip"
            if not mun_path.exists():
                await download_file(f"{RFB_BASE_URL}Municipios.zip", mun_path, session)
            mun_count = process_municipios_file(mun_path, db)
            logger.info(f"Municípios importados: {mun_count}")

            # Build lookup maps
            cnae_map = {c.codigo: c.descricao for c in db.query(Cnae).all()}
            municipio_map = {m.codigo: m.nome for m in db.query(Municipality).all()}

            db.query(ImportStatus).filter(ImportStatus.id == status_id).update({
                "status": "processing",
                "progress": 10.0
            })
            db.commit()

            # Step 3: Download and process Estabelecimentos
            all_cnpjs = set()
            total_companies = 0

            for i in range(file_count):
                file_name = f"Estabelecimentos{i}.zip"
                file_path = DOWNLOAD_DIR / file_name
                logger.info(f"Processando {file_name}...")

                if not file_path.exists():
                    success = await download_file(
                        f"{RFB_BASE_URL}{file_name}", file_path, session
                    )
                    if not success:
                        logger.warning(f"Falha ao baixar {file_name}, pulando...")
                        continue

                count, cnpjs = process_estabelecimentos_file(
                    file_path, db, uf, municipio_map, cnae_map
                )
                all_cnpjs.update(cnpjs)
                total_companies += count

                progress = 10 + (70 * (i + 1) / file_count)
                db.query(ImportStatus).filter(ImportStatus.id == status_id).update({
                    "progress": progress,
                    "records_imported": total_companies
                })
                db.commit()

                logger.info(f"{file_name}: {count} empresas de {uf} importadas")

                # Clean up downloaded file to save space
                if file_path.exists():
                    os.remove(file_path)

            # Step 4: Download and process Empresas (for razao_social)
            logger.info("Processando dados de Empresas (razão social)...")
            for i in range(file_count):
                file_name = f"Empresas{i}.zip"
                file_path = DOWNLOAD_DIR / file_name

                if not file_path.exists():
                    success = await download_file(
                        f"{RFB_BASE_URL}{file_name}", file_path, session
                    )
                    if not success:
                        continue

                result = process_empresas_file(file_path, db, all_cnpjs)
                update_razao_social(db, result["razao"], result["porte"])

                progress = 80 + (20 * (i + 1) / file_count)
                db.query(ImportStatus).filter(ImportStatus.id == status_id).update({
                    "progress": progress
                })
                db.commit()

                logger.info(f"{file_name}: razão social atualizada")

                # Clean up
                if file_path.exists():
                    os.remove(file_path)

            # Done!
            db.query(ImportStatus).filter(ImportStatus.id == status_id).update({
                "status": "done",
                "progress": 100.0,
                "records_imported": total_companies
            })
            db.commit()
            logger.info(f"Importação completa para {uf}: {total_companies} empresas")

    except Exception as e:
        logger.error(f"Erro na importação: {e}")
        db.query(ImportStatus).filter(ImportStatus.id == status_id).update({
            "status": "error",
            "error_message": str(e)
        })
        db.commit()
    finally:
        db.close()


def get_import_stats(db: Session) -> dict:
    """Get current data statistics."""
    total_companies = db.query(func.count(Company.id)).scalar() or 0
    total_cnaes = db.query(func.count(Cnae.id)).scalar() or 0
    total_municipalities = db.query(func.count(Municipality.id)).scalar() or 0
    states = [row[0] for row in db.query(Company.uf).distinct().all() if row[0]]

    return {
        "total_companies": total_companies,
        "total_cnaes": total_cnaes,
        "total_municipalities": total_municipalities,
        "states_imported": sorted(states)
    }
