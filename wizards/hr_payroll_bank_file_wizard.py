from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class HrPayrollBankFileWizard(models.TransientModel):
    _name = 'hr.payroll.bank.file.wizard'
    _description = 'Asistente de Archivo Bancario'

    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Lote de Nómina',
        required=True
    )

    bank_id = fields.Many2one(
        'res.bank',
        string='Banco',
        required=True
    )

    payment_date = fields.Date(
        string='Fecha de Pago',
        required=True,
        default=fields.Date.today
    )

    file_format = fields.Selection([
        ('bancolombia_pab', 'Bancolombia PAB'),
        ('bancolombia_sap', 'Bancolombia SAP'),
        ('davivienda_pab', 'Davivienda PAB'),
        ('bbva_excel', 'BBVA Excel'),
        ('popular_txt', 'Banco Popular TXT'),
        ('occidente_txt', 'Banco Occidente TXT'),
        ('bogota_txt', 'Banco Bogotá TXT')
    ], string='Formato de Archivo', required=True)

    payment_type = fields.Selection([
        ('salary', 'Nómina'),
        ('prima', 'Prima'),
        ('cesantias', 'Cesantías'),
        ('interest', 'Intereses Cesantías'),
        ('bonus', 'Bonificaciones'),
        ('other', 'Otros Pagos')
    ], string='Tipo de Pago', required=True, default='salary')

    include_provisions = fields.Boolean(
        string='Incluir Provisiones',
        help='Incluir pagos de provisiones en el archivo'
    )

    only_provisions = fields.Boolean(
        string='Solo Provisiones',
        help='Generar archivo solo con pagos de provisiones'
    )

    group_by_department = fields.Boolean(
        string='Agrupar por Departamento',
        help='Generar archivos separados por departamento'
    )

    reference = fields.Char(
        string='Referencia de Pago',
        help='Referencia que aparecerá en el extracto bancario'
    )

    description = fields.Text(
        string='Descripción',
        help='Descripción adicional para el archivo'
    )

    @api.model
    def default_get(self, fields_list):
        """Valores por defecto del wizard"""
        res = super(HrPayrollBankFileWizard, self).default_get(fields_list)
        active_id = self._context.get('active_id')
        
        if active_id:
            payslip_run = self.env['hr.payslip.run'].browse(active_id)
            res.update({
                'payslip_run_id': payslip_run.id,
                'payment_date': payslip_run.date_end,
                'reference': f"NOMINA_{payslip_run.date_end.strftime('%Y%m')}"
            })
        return res

    @api.onchange('bank_id')
    def _onchange_bank_id(self):
        """Actualiza formato de archivo según banco seleccionado"""
        if self.bank_id:
            if 'BANCOLOMBIA' in self.bank_id.name.upper():
                self.file_format = 'bancolombia_pab'
            elif 'DAVIVIENDA' in self.bank_id.name.upper():
                self.file_format = 'davivienda_pab'
            elif 'BBVA' in self.bank_id.name.upper():
                self.file_format = 'bbva_excel'
            elif 'POPULAR' in self.bank_id.name.upper():
                self.file_format = 'popular_txt'
            elif 'OCCIDENTE' in self.bank_id.name.upper():
                self.file_format = 'occidente_txt'
            elif 'BOGOTA' in self.bank_id.name.upper():
                self.file_format = 'bogota_txt'

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        """Actualiza referencia según tipo de pago"""
        if self.payment_type and self.payslip_run_id:
            prefix = dict(self._fields['payment_type'].selection).get(self.payment_type).upper()
            self.reference = f"{prefix}_{self.payslip_run_id.date_end.strftime('%Y%m')}"

    def action_generate_file(self):
        """Genera archivo bancario según el formato seleccionado"""
        self.ensure_one()
        
        if not self.payslip_run_id.slip_ids:
            raise ValidationError(_('No hay nóminas en el lote seleccionado'))

        try:
            # Validar empleados sin cuenta bancaria
            employees_without_account = self.payslip_run_id.slip_ids.filtered(
                lambda x: not x.employee_id.bank_account_id
            ).mapped('employee_id.name')
            
            if employees_without_account:
                raise ValidationError(_(
                    'Los siguientes empleados no tienen cuenta bancaria configurada:\n%s'
                ) % '\n'.join(employees_without_account))

            # Generar archivo(s)
            if self.group_by_department:
                return self._generate_files_by_department()
            else:
                return self._generate_single_file()

        except Exception as e:
            raise ValidationError(_('Error generando archivo: %s') % str(e))

    def _generate_single_file(self):
        """Genera un único archivo bancario"""
        # Obtener método según formato
        method_name = f'_generate_{self.file_format}_content'
        if not hasattr(self, method_name):
            raise ValidationError(_('Formato de archivo no implementado'))

        # Generar contenido
        content = getattr(self, method_name)(self.payslip_run_id.slip_ids)
        
        # Crear nombre del archivo
        filename = self._get_filename()

        # Crear adjunto
        attachment = self._create_attachment(content, filename)

        # Actualizar lote de nómina
        self.payslip_run_id.write({
            'bank_file': attachment.datas,
            'bank_file_name': filename
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _generate_files_by_department(self):
        """Genera archivos separados por departamento"""
        attachments = []
        
        # Agrupar nóminas por departamento
        payslips_by_department = {}
        for slip in self.payslip_run_id.slip_ids:
            dept_id = slip.employee_id.department_id.id
            if dept_id not in payslips_by_department:
                payslips_by_department[dept_id] = self.env['hr.payslip']
            payslips_by_department[dept_id] |= slip

        # Generar archivo por departamento
        for dept_id, payslips in payslips_by_department.items():
            department = self.env['hr.department'].browse(dept_id)
            
            # Obtener contenido
            method_name = f'_generate_{self.file_format}_content'
            content = getattr(self, method_name)(payslips)
            
            # Crear nombre del archivo
            filename = self._get_filename(department=department)
            
            # Crear adjunto
            attachment = self._create_attachment(content, filename)
            attachments.append(attachment.id)

        # Retornar acción para descargar archivos
        return {
            'type': 'ir.actions.act_window',
            'name': _('Archivos Bancarios'),
            'res_model': 'ir.attachment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', attachments)],
            'target': 'current',
        }

    def _create_attachment(self, content, filename):
        """Crea adjunto con el contenido del archivo"""
        return self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(content.encode('utf-8')),
            'mimetype': 'text/plain',
            'res_model': 'hr.payslip.run',
            'res_id': self.payslip_run_id.id,
        })

    def _get_filename(self, department=None):
        """Genera nombre del archivo"""
        parts = [
            self.payment_type.upper(),
            self.bank_id.name.upper().replace(' ', '_'),
            self.payslip_run_id.date_end.strftime('%Y%m%d')
        ]
        
        if department:
            parts.append(department.name.upper().replace(' ', '_'))
            
        parts.append(datetime.now().strftime('%H%M%S'))
        
        return f"{'_'.join(parts)}.txt"

    def _generate_bancolombia_pab_content(self, payslips):
        """Genera contenido formato Bancolombia PAB"""
        content = []
        total_amount = 0
        count = 0

        # Encabezado
        header = (
            "1"  # Tipo registro
            f"{self.payslip_run_id.company_id.vat:>10}"  # NIT empresa
            f"{datetime.now().strftime('%Y%m%d'):8}"  # Fecha generación
            f"{self.payment_date.strftime('%Y%m%d'):8}"  # Fecha pago
            "225"  # Código transacción
            f"{self.reference[:16]:<16}"  # Descripción
            f"{' '*40}"  # Relleno
        )
        content.append(header)

        # Detalle
        for slip in payslips:
            amount = self._get_payment_amount(slip)
            if not amount:
                continue

            detail = (
                "2"  # Tipo registro
                f"{slip.employee_id.bank_account_id.acc_number:>16}"  # Cuenta
                f"{amount:015.2f}"  # Valor
                f"{slip.employee_id.identification_id:>15}"  # Documento
                f"{slip.employee_id.name:<30}"  # Nombre
                f"{' '*20}"  # Relleno
            )
            content.append(detail)
            total_amount += amount
            count += 1

        # Pie
        footer = (
            "3"  # Tipo registro
            f"{count:06d}"  # Total registros
            f"{total_amount:015.2f}"  # Total valor
            f"{' '*74}"  # Relleno
        )
        content.append(footer)

        return '\n'.join(content)

    def _get_payment_amount(self, payslip):
        """Calcula monto a pagar según configuración"""
        amount = 0
        
        if not self.only_provisions:
            amount += payslip.net_wage
            
        if self.include_provisions or self.only_provisions:
            if self.payment_type == 'prima':
                amount += payslip.prima_amount
            elif self.payment_type == 'cesantias':
                amount += payslip.cesantias_amount
            elif self.payment_type == 'interest':
                amount += payslip.cesantias_interest_amount
                
        return amount

    def _generate_bancolombia_sap_content(self, payslips):
        """Genera contenido formato Bancolombia SAP"""
        content = []
        total_amount = 0
        count = 0

        # Encabezado SAP
        header = (
            "1"  # Indicador de registro de control
            f"{self.payslip_run_id.company_id.vat:>11}"  # NIT empresa sin DV
            f"{self.payment_date.strftime('%Y%m%d')}"  # Fecha de pago
            f"{self.reference[:30]:<30}"  # Referencia del pago
            "COP"  # Moneda
            "S"  # Tipo de cuenta (S=Savings, C=Current)
            f"{self.payslip_run_id.company_id.bank_account_id.acc_number:>11}"  # Cuenta débito
            f"{' '*42}"  # Espacios en blanco
        )
        content.append(header)

        # Registros detalle
        for slip in payslips:
            amount = self._get_payment_amount(slip)
            if not amount:
                continue

            detail = (
                "2"  # Indicador de registro detalle
                f"{slip.employee_id.identification_id:>15}"  # Documento beneficiario
                f"{slip.employee_id.name[:30]:<30}"  # Nombre beneficiario
                f"{amount:015.2f}"  # Valor
                f"{slip.employee_id.bank_account_id.acc_number:>11}"  # Cuenta beneficiario
                "S"  # Tipo cuenta beneficiario
                f"{self.description[:40]:<40}"  # Descripción
                "0"  # Indicador de correo
                f"{' '*15}"  # Espacios en blanco
            )
            content.append(detail)
            total_amount += amount
            count += 1

        # Registro control
        footer = (
            "3"  # Indicador de registro de control
            f"{count:06d}"  # Cantidad de registros
            f"{total_amount:015.2f}"  # Valor total
            f"{' '*79}"  # Espacios en blanco
        )
        content.append(footer)

        return '\n'.join(content)

    def _generate_davivienda_pab_content(self, payslips):
        """Genera contenido formato Davivienda PAB"""
        content = []
        total_amount = 0
        count = 0

        # Encabezado
        header = (
            "01"  # Tipo registro
            f"{self.payslip_run_id.company_id.vat:>10}"  # NIT empresa
            f"{datetime.now().strftime('%Y%m%d')}"  # Fecha de generación
            f"{self.payment_date.strftime('%Y%m%d')}"  # Fecha de pago
            "1"  # Tipo de cuenta (1=Ahorros, 2=Corriente)
            f"{self.payslip_run_id.company_id.bank_account_id.acc_number:>16}"  # Cuenta débito
            f"{self.reference[:30]:<30}"  # Descripción del pago
            f"{' '*33}"  # Filler
        )
        content.append(header)

        # Detalle de pagos
        for slip in payslips:
            amount = self._get_payment_amount(slip)
            if not amount:
                continue

            detail = (
                "02"  # Tipo registro
                f"{slip.employee_id.identification_id:>15}"  # Documento
                f"{slip.employee_id.name[:30]:<30}"  # Nombre
                "1"  # Tipo de cuenta (1=Ahorros, 2=Corriente)
                f"{slip.employee_id.bank_account_id.acc_number:>16}"  # Cuenta
                f"{amount:015.2f}"  # Valor
                "0"  # Tipo de identificación (0=CC, 1=NIT)
                f"{self.description[:40]:<40}"  # Referencia
            )
            content.append(detail)
            total_amount += amount
            count += 1

        # Totales
        footer = (
            "03"  # Tipo registro
            f"{count:06d}"  # Número de registros
            f"{total_amount:015.2f}"  # Valor total
            f"{' '*77}"  # Filler
        )
        content.append(footer)

        return '\n'.join(content)

    def _generate_bbva_excel_content(self, payslips):
        """Genera contenido formato BBVA Excel"""
        import xlsxwriter
        from io import BytesIO

        # Crear archivo Excel en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Pagos')

        # Formatos
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#CCCCCC'
        })

        # Encabezados
        headers = [
            'Tipo Documento', 'Número Documento', 'Nombre Beneficiario',
            'Tipo Cuenta', 'Número Cuenta', 'Valor', 'Concepto'
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Datos
        row = 1
        total_amount = 0
        for slip in payslips:
            amount = self._get_payment_amount(slip)
            if not amount:
                continue

            worksheet.write(row, 0, 'CC')  # Tipo documento
            worksheet.write(row, 1, slip.employee_id.identification_id)
            worksheet.write(row, 2, slip.employee_id.name)
            worksheet.write(row, 3, 'AHORROS')
            worksheet.write(row, 4, slip.employee_id.bank_account_id.acc_number)
            worksheet.write(row, 5, amount)
            worksheet.write(row, 6, self.reference)
            
            total_amount += amount
            row += 1

        # Totales
        worksheet.write(row + 1, 4, 'Total:', header_format)
        worksheet.write(row + 1, 5, total_amount)

        workbook.close()
        return output.getvalue()

    def _generate_popular_txt_content(self, payslips):
        """Genera contenido formato Banco Popular"""
        content = []
        total_amount = 0
        count = 0

        # Encabezado
        header = (
            "01"  # Tipo registro
            f"{self.payslip_run_id.company_id.vat:>11}"  # NIT empresa
            f"{self.payment_date.strftime('%Y%m%d')}"  # Fecha de pago
            f"{self.reference[:20]:<20}"  # Referencia
            f"{' '*67}"  # Filler
        )
        content.append(header)

        # Detalle
        for slip in payslips:
            amount = self._get_payment_amount(slip)
            if not amount:
                continue

            detail = (
                "02"  # Tipo registro
                f"{slip.employee_id.identification_id:>11}"  # Documento
                f"{slip.employee_id.name[:30]:<30}"  # Nombre
                f"{slip.employee_id.bank_account_id.acc_number:>16}"  # Cuenta
                f"{amount:013.2f}"  # Valor
                "10"  # Tipo de cuenta (10=Ahorros, 20=Corriente)
                f"{self.description[:28]:<28}"  # Descripción
            )
            content.append(detail)
            total_amount += amount
            count += 1

        # Control
        footer = (
            "03"  # Tipo registro
            f"{count:06d}"  # Cantidad registros
            f"{total_amount:015.2f}"  # Total
            f"{' '*79}"  # Filler
        )
        content.append(footer)

        return '\n'.join(content)

    def _generate_occidente_txt_content(self, payslips):
        """Genera contenido formato Banco Occidente"""
        content = []
        total_amount = 0
        count = 0

        # Encabezado
        header = (
            "1"  # Tipo registro
            f"{self.payslip_run_id.company_id.vat:>11}"  # NIT empresa
            f"{self.payment_date.strftime('%Y%m%d')}"  # Fecha de pago
            f"{self.payslip_run_id.company_id.bank_account_id.acc_number:>11}"  # Cuenta débito
            "09"  # Tipo de pago (09=Nómina)
            f"{self.reference[:10]:<10}"  # Referencia
            f"{' '*55}"  # Filler
        )
        content.append(header)

        # Detalle
        for slip in payslips:
            amount = self._get_payment_amount(slip)
            if not amount:
                continue

            detail = (
                "2"  # Tipo registro
                f"{slip.employee_id.identification_id:>11}"  # Documento
                f"{slip.employee_id.name[:30]:<30}"  # Nombre
                f"{slip.employee_id.bank_account_id.acc_number:>11}"  # Cuenta
                "A"  # Tipo cuenta (A=Ahorros, C=Corriente)
                f"{amount:013.2f}"  # Valor
                f"{self.description[:30]:<30}"  # Descripción
            )
            content.append(detail)
            total_amount += amount
            count += 1

        # Totales
        footer = (
            "3"  # Tipo registro
            f"{count:06d}"  # Cantidad registros
            f"{total_amount:015.2f}"  # Total
            f"{' '*79}"  # Filler
        )
        content.append(footer)

        return '\n'.join(content)

    def _generate_bogota_txt_content(self, payslips):
        """Genera contenido formato Banco Bogotá"""
        content = []
        total_amount = 0
        count = 0

        # Encabezado
        header = (
            "01"  # Tipo registro
            f"{self.payment_date.strftime('%Y%m%d')}"  # Fecha de pago
            f"{self.payslip_run_id.company_id.vat:>11}"  # NIT empresa
            f"{self.payslip_run_id.company_id.name[:20]:<20}"  # Nombre empresa
            f"{self.payslip_run_id.company_id.bank_account_id.acc_number:>11}"  # Cuenta débito
            "S"  # Tipo cuenta (S=Ahorros, D=Corriente)
            f"{self.reference[:12]:<12}"  # Referencia
            f"{' '*35}"  # Filler
        )
        content.append(header)

        # Detalle
        for slip in payslips:
            amount = self._get_payment_amount(slip)
            if not amount:
                continue

            detail = (
                "02"  # Tipo registro
                f"{slip.employee_id.identification_id:>11}"  # Documento
                f"{slip.employee_id.name[:30]:<30}"  # Nombre
                f"{slip.employee_id.bank_account_id.acc_number:>11}"  # Cuenta
                "S"  # Tipo cuenta (S=Ahorros, D=Corriente)
                f"{amount:013.2f}"  # Valor
                "00"  # Oficina
                f"{self.description[:30]:<30}"  # Descripción
            )
            content.append(detail)
            total_amount += amount
            count += 1

        # Control
        footer = (
            "03"  # Tipo registro
            f"{count:06d}"  # Cantidad registros
            f"{total_amount:015.2f}"  # Total
            f"{' '*79}"  # Filler
        )
        content.append(footer)

        return '\n'.join(content)