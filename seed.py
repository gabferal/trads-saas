"""
seed.py – Popula o banco com dados de exemplo realistas para um escritório de
traduções espanhol → português (documentos paraguaios/argentinos comuns).

Execute: python seed.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta, timezone
from app.database import SessionLocal, engine
from app.models import Base, User, Client, ServiceOrder, Batch, Document, Financial, AuditLog
from app.models import StatusOS, StatusDocumento, StatusMalote, TipoFinanceiro
from app.auth import hash_senha

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── Limpar dados existentes (ordem inversa das FK) ────────────────────
        db.query(AuditLog).delete()
        db.query(Financial).delete()
        db.query(Document).delete()
        db.query(Batch).delete()
        db.query(ServiceOrder).delete()
        db.query(Client).delete()
        db.query(User).delete()
        db.commit()

        agora = datetime.now(timezone.utc)

        # ── Usuários ──────────────────────────────────────────────────────────
        user1 = User(nome="Mariana Oliveira", email="mariana@translacoes.com", senha_hash=hash_senha("admin123"))
        user2 = User(nome="Carlos Ferreira",  email="carlos@translacoes.com",  senha_hash=hash_senha("admin123"))
        db.add_all([user1, user2])
        db.flush()

        # ── Clientes ──────────────────────────────────────────────────────────
        clientes = [
            Client(nome_completo="Juan Carlos Rodríguez Ortiz",  telefone_whatsapp="595981234567"),
            Client(nome_completo="María Elena Gonzáles Paredes",  telefone_whatsapp="595991234568"),
            Client(nome_completo="Luis Alberto Méndez Torres",     telefone_whatsapp="595971234569"),
            Client(nome_completo="Ana Paula Acosta Villalba",      telefone_whatsapp="595961234570"),
            Client(nome_completo="Roberto Ariel Benítez Sosa",     telefone_whatsapp="595991234571"),
        ]
        db.add_all(clientes)
        db.flush()

        # ── Malotes ───────────────────────────────────────────────────────────
        mal1 = Batch(
            codigo_identificacao="MAL-2026-001",
            data_envio=agora - timedelta(days=10),
            status=StatusMalote.entregue,
        )
        mal2 = Batch(
            codigo_identificacao="MAL-2026-002",
            data_envio=agora - timedelta(days=3),
            status=StatusMalote.em_transito,
        )
        mal3 = Batch(
            codigo_identificacao="MAL-2026-003",
            status=StatusMalote.aberto,
        )
        db.add_all([mal1, mal2, mal3])
        db.flush()

        # ── Ordens de Serviço ─────────────────────────────────────────────────
        os1 = ServiceOrder(cliente_id=clientes[0].id, status_geral=StatusOS.concluida,
                           data_abertura=agora - timedelta(days=20),
                           descricao="Revalidação de diploma universitário - UNA")
        os2 = ServiceOrder(cliente_id=clientes[1].id, status_geral=StatusOS.em_andamento,
                           data_abertura=agora - timedelta(days=12),
                           descricao="Documentação acadêmica para mestrado no Brasil")
        os3 = ServiceOrder(cliente_id=clientes[2].id, status_geral=StatusOS.em_andamento,
                           data_abertura=agora - timedelta(days=5),
                           descricao="Legalização documentos pessoais + tradução")
        os4 = ServiceOrder(cliente_id=clientes[3].id, status_geral=StatusOS.aberta,
                           data_abertura=agora - timedelta(days=1),
                           descricao="Reconhecimento de título - Medicina UNIBE")
        os5 = ServiceOrder(cliente_id=clientes[4].id, status_geral=StatusOS.aberta,
                           data_abertura=agora,
                           descricao="Apostilamento e tradução de certidões")
        db.add_all([os1, os2, os3, os4, os5])
        db.flush()

        # ── Documentos (com hierarquia pai/filho) ─────────────────────────────

        # OS1 – concluída, vinculada ao MAL-2026-001
        doc1_pai = Document(
            os_id=os1.id, malote_id=mal1.id,
            tipo_documento="Plan de Estudios (Plano Analítico)",
            status_documento=StatusDocumento.finalizado,
            idioma_origem="Espanhol", idioma_destino="Português",
            snapshot_url="https://storage.example.com/snap/os1_plan.jpg",
        )
        db.add(doc1_pai); db.flush()

        doc1_filho1 = Document(
            os_id=os1.id, malote_id=mal1.id, pai_id=doc1_pai.id,
            tipo_documento="Programa de Estudios – 1º Ano",
            status_documento=StatusDocumento.finalizado,
            snapshot_url="https://storage.example.com/snap/os1_prog1.jpg",
        )
        doc1_filho2 = Document(
            os_id=os1.id, malote_id=mal1.id, pai_id=doc1_pai.id,
            tipo_documento="Constancia de Calificaciones – 1º Ano",
            status_documento=StatusDocumento.finalizado,
            snapshot_url="https://storage.example.com/snap/os1_cal1.jpg",
        )
        doc1_filho3 = Document(
            os_id=os1.id, malote_id=mal1.id, pai_id=doc1_pai.id,
            tipo_documento="Ementa de Disciplinas – Ciências Contábeis",
            status_documento=StatusDocumento.finalizado,
        )
        db.add_all([doc1_filho1, doc1_filho2, doc1_filho3])

        # OS2 – em andamento, parte no MAL-2026-002, parte sem malote
        doc2_pai = Document(
            os_id=os2.id, malote_id=mal2.id,
            tipo_documento="Plan de Estudios (Plano Analítico) – Medicina",
            status_documento=StatusDocumento.em_transito,
        )
        db.add(doc2_pai); db.flush()

        doc2_filho1 = Document(
            os_id=os2.id, malote_id=mal2.id, pai_id=doc2_pai.id,
            tipo_documento="Certificado de Calificaciones – Ciclo Básico",
            status_documento=StatusDocumento.em_transito,
            snapshot_url="https://storage.example.com/snap/os2_cert.jpg",
        )
        doc2_filho2 = Document(
            os_id=os2.id, malote_id=None, pai_id=doc2_pai.id,  # atrasado, sem malote ainda
            tipo_documento="Histórico Escolar – Ensino Médio",
            status_documento=StatusDocumento.em_traducao,
        )
        doc2_avulso = Document(
            os_id=os2.id, malote_id=mal2.id,
            tipo_documento="Acta de Nacimiento (Certidão de Nascimento)",
            status_documento=StatusDocumento.traduzido,
            snapshot_url="https://storage.example.com/snap/os2_acta.jpg",
        )
        db.add_all([doc2_filho1, doc2_filho2, doc2_avulso])

        # OS3 – em andamento
        doc3a = Document(
            os_id=os3.id, malote_id=mal3.id,
            tipo_documento="Cédula de Identidad (RG/CPF equivalente)",
            status_documento=StatusDocumento.traduzido,
        )
        doc3b = Document(
            os_id=os3.id, malote_id=None,
            tipo_documento="Certificado de Antecedentes Policiales",
            status_documento=StatusDocumento.em_traducao,
            observacoes="Aguardando apostila antes de traduzir",
        )
        db.add_all([doc3a, doc3b])

        # OS4 e OS5 – recém abertas, sem malote
        doc4a = Document(
            os_id=os4.id,
            tipo_documento="Plan de Estudios (Plano Analítico) – Odontología",
            status_documento=StatusDocumento.recebido,
        )
        doc4b = Document(
            os_id=os4.id,
            tipo_documento="Diploma de Graduación",
            status_documento=StatusDocumento.recebido,
        )
        doc5a = Document(
            os_id=os5.id,
            tipo_documento="Partida de Nacimiento (Certidão de Nascimento)",
            status_documento=StatusDocumento.recebido,
        )
        doc5b = Document(
            os_id=os5.id,
            tipo_documento="Matrimonio Civil (Certidão de Casamento)",
            status_documento=StatusDocumento.recebido,
        )
        db.add_all([doc4a, doc4b, doc5a, doc5b])

        # ── Financeiro ────────────────────────────────────────────────────────
        lancamentos = [
            Financial(os_id=os1.id, tipo=TipoFinanceiro.entrada, descricao="Serviço de tradução juramentada – OS#1",
                      valor=850.00, nf_lancada=True,
                      data_registro=agora - timedelta(days=15)),
            Financial(os_id=os1.id, tipo=TipoFinanceiro.saida, descricao="Taxas cartoriais – OS#1",
                      valor=120.00, nf_lancada=True,
                      data_registro=agora - timedelta(days=14)),
            Financial(os_id=os2.id, tipo=TipoFinanceiro.entrada, descricao="Adiantamento 50% – OS#2",
                      valor=600.00, nf_lancada=False,
                      data_registro=agora - timedelta(days=10)),
            Financial(os_id=os2.id, tipo=TipoFinanceiro.entrada, descricao="Pagamento restante – OS#2",
                      valor=600.00, nf_lancada=False,
                      data_registro=agora - timedelta(days=2)),
            Financial(os_id=os3.id, tipo=TipoFinanceiro.entrada, descricao="Tradução documentos pessoais – OS#3",
                      valor=350.00, nf_lancada=False,
                      data_registro=agora - timedelta(days=4)),
            Financial(os_id=os4.id, tipo=TipoFinanceiro.entrada, descricao="Sinal de serviço – OS#4",
                      valor=200.00, nf_lancada=False,
                      data_registro=agora - timedelta(days=1)),
        ]
        db.add_all(lancamentos)

        # ── Logs de Auditoria de exemplo ──────────────────────────────────────
        logs = [
            AuditLog(user_id=user1.id, acao="Criou Malote MAL-2026-001",
                     entidade_afetada="Batch:1", data_hora=agora - timedelta(days=20)),
            AuditLog(user_id=user1.id, acao="Alterou Status Malote: Aberto → Em Trânsito para Assunção",
                     entidade_afetada="Batch:1", data_hora=agora - timedelta(days=12)),
            AuditLog(user_id=user2.id, acao="Alterou Status Documento: Em Trânsito → Finalizado",
                     entidade_afetada="Document:1", data_hora=agora - timedelta(days=8)),
            AuditLog(user_id=user1.id, acao="Lançou NF no sistema tributário externo",
                     entidade_afetada="Financial:1", data_hora=agora - timedelta(days=14)),
            AuditLog(user_id=user2.id, acao="Criou Malote MAL-2026-002",
                     entidade_afetada="Batch:2", data_hora=agora - timedelta(days=5)),
        ]
        db.add_all(logs)

        db.commit()
        print("✅ Seed concluído com sucesso!")
        print(f"   • {len(clientes)} clientes")
        print(f"   • 5 ordens de serviço")
        print(f"   • 3 malotes (MAL-2026-001 a 003)")
        print(f"   • Múltiplos documentos com hierarquia pai/filho")
        print(f"   • {len(lancamentos)} lançamentos financeiros")
        print(f"\n   👤 Login: mariana@translacoes.com / admin123")

    except Exception as e:
        db.rollback()
        print(f"❌ Erro no seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
