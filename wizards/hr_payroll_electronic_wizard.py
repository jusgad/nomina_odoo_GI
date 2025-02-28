from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import base64
import hashlib
import json
import requests
import logging
from xml.etree import ElementTree as ET

_logger = logging.getLogger(__name__)

class HrPayrollElectronicWizard(models.TransientModel):
    _name = 'hr.payroll.electronic.wizard'
    _description = 'Asistente de Nómina Electrónica'

    # Campos Básicos
    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Lote de Nómina',
        required=True
    )

    date_from = fields.Date(
        string='Fecha Inicial',
        required=True
    )

    date_to = fields.Date(
        string='Fecha Final',
        required=True
    )

    document_type = fields.Selection([
        ('102', 'Nómina Individual'),
        ('103', 'Nómina Individual de Ajuste'),
        ('104', 'Nómina de Liquidación'),
    ], string='Tipo de Documento', required=True, default='102')

    # Campos de Configuración
    environment = fields.Selection([
        ('1', 'Producción'),
        ('2', 'Pruebas')
    ], string='Ambiente', required=True, default='2')

    sync_mode = fields.Selection([
        ('sync', 'Síncrono'),
        ('async', 'Asíncrono')
    ], string='Modo de Envío', required=True, default='sync')

    # Campos de Control
    include_adjustments = fields.Boolean(
        string='Incluir Ajustes',
        help='Incluir ajustes de nóminas anteriores'
    )

    generate_pdf = fields.Boolean(
        string='Generar PDF',
        default=True,
        help='Generar representación gráfica en PDF'
    )

    validate_only = fields.Boolean(
        string='Solo Validar',
        help='Realizar solo validación sin enviar a la DIAN'
    )

    notes = fields.Text(
        string='Notas',
        help='Notas adicionales para el documento'
    )

    # Campos Técnicos
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )

    preview_xml = fields.Text(
        string='Vista Previa XML',
        readonly=True
    )

    @api.model
    def default_get(self, fields_list):
        """Valores por defecto del wizard"""
        res = super(HrPayrollElectronicWizard, self).default_get(fields_list)
        active_id = self._context.get('active_id')
        
        if active_id:
            payslip_run = self.env['hr.payslip.run'].browse(active_id)
            res.update({
                'payslip_run_id': payslip_run.id,
                'date_from': payslip_run.date_start,
                'date_to': payslip_run.date_end,
                'environment': self.env.company.dian_environment
            })
        return res

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Validar fechas"""
        for record in self:
            if record.date_to < record.date_from:
                raise ValidationError(_('La fecha final debe ser mayor a la fecha inicial'))

    def action_generate_electronic_payroll(self):
        """Genera documentos de nómina electrónica"""
        self.ensure_one()

        try:
            # Validar configuración
            self._validate_configuration()

            # Validar nóminas
            self._validate_payslips()

            # Crear documento electrónico
            electronic_doc = self._create_electronic_document()

            # Generar XML
            xml_content = self._generate_xml_content(electronic_doc)

            # Firmar XML
            signed_xml = self._sign_xml(xml_content)

            # Validar y/o enviar a DIAN
            if self.validate_only:
                response = self._validate_with_dian(signed_xml)
            else:
                response = self._send_to_dian(signed_xml)

            # Procesar respuesta
            self._process_dian_response(electronic_doc, response)

            # Generar PDF si es necesario
            if self.generate_pdf:
                self._generate_pdf(electronic_doc)

            return self._get_result_action(electronic_doc)

        except Exception as e:
            _logger.error("Error en nómina electrónica: %s", str(e))
            raise ValidationError(_('Error en proceso de nómina electrónica: %s') % str(e))

    def _validate_configuration(self):
        """Valida la configuración necesaria"""
        company = self.company_id
        
        # Validar configuración DIAN
        if not company.dian_software_id:
            raise ValidationError(_('Falta configurar el ID del software DIAN'))
            
        if not company.dian_software_pin:
            raise ValidationError(_('Falta configurar el PIN del software DIAN'))
            
        if not company.digital_certificate:
            raise ValidationError(_('Falta configurar el certificado digital'))
            
        if not company.digital_certificate_password:
            raise ValidationError(_('Falta configurar la contraseña del certificado digital'))

        # Validar fechas de resolución
        if not company.dian_resolution_number:
            raise ValidationError(_('Falta configurar el número de resolución DIAN'))
            
        if company.dian_resolution_date_to and company.dian_resolution_date_to < fields.Date.today():
            raise ValidationError(_('La resolución DIAN está vencida'))

    def _validate_payslips(self):
        """Valida las nóminas del lote"""
        if not self.payslip_run_id.slip_ids:
            raise ValidationError(_('No hay nóminas en el lote seleccionado'))

        # Validar estado de las nóminas
        invalid_payslips = self.payslip_run_id.slip_ids.filtered(
            lambda x: x.state not in ['done', 'paid']
        )
        if invalid_payslips:
            raise ValidationError(_(
                'Las siguientes nóminas no están en estado válido:\n%s'
            ) % '\n'.join(invalid_payslips.mapped('name')))

        # Validar información requerida
        for payslip in self.payslip_run_id.slip_ids:
            if not payslip.employee_id.identification_id:
                raise ValidationError(_(
                    'El empleado %s no tiene número de identificación'
                ) % payslip.employee_id.name)

    def _create_electronic_document(self):
        """Crea el documento de nómina electrónica"""
        return self.env['hr.electronic.payroll'].create({
            'name': f"NE-{self.payslip_run_id.name}",
            'company_id': self.company_id.id,
            'payslip_run_id': self.payslip_run_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'document_type': self.document_type,
            'environment': self.environment,
            'notes': self.notes,
            'state': 'draft'
        })

    def _generate_xml_content(self, electronic_doc):
        """Genera el contenido XML del documento"""
        # Crear estructura base XML
        root = ET.Element('NominaIndividual')
        
        # Agregar encabezado
        header = self._generate_xml_header(electronic_doc)
        root.append(header)
        
        # Agregar información empleador
        employer = self._generate_xml_employer()
        root.append(employer)
        
        # Agregar información trabajador y pagos para cada nómina
        for payslip in self.payslip_run_id.slip_ids:
            worker = self._generate_xml_worker(payslip)
            root.append(worker)
            
            payment = self._generate_xml_payment(payslip)
            root.append(payment)
            
            deductions = self._generate_xml_deductions(payslip)
            root.append(deductions)

        # Convertir a string
        return ET.tostring(root, encoding='UTF-8', xml_declaration=True)

    def _generate_xml_header(self, electronic_doc):
        """Genera sección de encabezado del XML"""
        header = ET.Element('Encabezado')
        
        # Información básica
        ET.SubElement(header, 'Version').text = '1.0'
        ET.SubElement(header, 'Ambiente').text = self.environment
        ET.SubElement(header, 'TipoDocumento').text = self.document_type
        ET.SubElement(header, 'FechaGeneracion').text = fields.Datetime.now().isoformat()
        ET.SubElement(header, 'PeriodoNomina').text = f"{self.date_from.strftime('%Y-%m-%d')}/{self.date_to.strftime('%Y-%m-%d')}"
        
        # Información DIAN
        ET.SubElement(header, 'SoftwareID').text = self.company_id.dian_software_id
        ET.SubElement(header, 'NumeroResolucion').text = self.company_id.dian_resolution_number
        
        return header

    def _generate_xml_employer(self):
        """Genera sección de empleador del XML"""
        employer = ET.Element('Empleador')
        company = self.company_id
        
        # Información básica
        ET.SubElement(employer, 'RazonSocial').text = company.name
        ET.SubElement(employer, 'NIT').text = company.vat
        ET.SubElement(employer, 'DV').text = company.vat_dv
        ET.SubElement(employer, 'Direccion').text = company.street
        ET.SubElement(employer, 'Municipio').text = company.city
        ET.SubElement(employer, 'Departamento').text = company.state_id.name
        
        return employer

    def _generate_xml_worker(self, payslip):
        """Genera sección de trabajador del XML"""
        worker = ET.Element('Trabajador')
        employee = payslip.employee_id
        
        # Información básica
        ET.SubElement(worker, 'TipoDocumento').text = employee.identification_type
        ET.SubElement(worker, 'NumeroDocumento').text = employee.identification_id
        ET.SubElement(worker, 'PrimerNombre').text = employee.first_name
        ET.SubElement(worker, 'PrimerApellido').text = employee.last_name
        ET.SubElement(worker, 'SalarioIntegral').text = 'true' if payslip.contract_id.wage_type == 'integral' else 'false'
        ET.SubElement(worker, 'TipoContrato').text = payslip.contract_id.contract_type
        
        return worker

    def _generate_xml_payment(self, payslip):
        """Genera sección de pago del XML"""
        payment = ET.Element('Pago')
        
        # Información básica
        ET.SubElement(payment, 'Periodo').text = payslip.date_from.strftime('%Y-%m')
        ET.SubElement(payment, 'FechaPago').text = payslip.date_to.strftime('%Y-%m-%d')
        
        # Devengados
        earnings = ET.SubElement(payment, 'Devengados')
        for line in payslip.line_ids.filtered(lambda l: l.category_id.code == 'BASIC'):
            earning = ET.SubElement(earnings, 'Basico')
            ET.SubElement(earning, 'DiasTrabajados').text = str(int(line.quantity))
            ET.SubElement(earning, 'SueldoTrabajado').text = str(line.total)
        
        return payment

    def _generate_xml_deductions(self, payslip):
        """Genera sección de deducciones del XML"""
        deductions = ET.Element('Deducciones')
        
        # Salud
        health = payslip.line_ids.filtered(lambda l: l.code == 'HEALTH')
        if health:
            health_elem = ET.SubElement(deductions, 'Salud')
            ET.SubElement(health_elem, 'Porcentaje').text = str(abs(health.rate))
            ET.SubElement(health_elem, 'Valor').text = str(abs(health.total))
        
        # Pensión
        pension = payslip.line_ids.filtered(lambda l: l.code == 'PENSION')
        if pension:
            pension_elem = ET.SubElement(deductions, 'Pension')
            ET.SubElement(pension_elem, 'Porcentaje').text = str(abs(pension.rate))
            ET.SubElement(pension_elem, 'Valor').text = str(abs(pension.total))
        
        return deductions

    def _sign_xml(self, xml_content):
        """Firma el XML con el certificado digital"""
        try:
            # Implementar firma digital según especificaciones DIAN
            # Este es un proceso complejo que requiere uso de librerías específicas
            return xml_content
        except Exception as e:
            raise ValidationError(_('Error firmando XML: %s') % str(e))

    def _validate_with_dian(self, signed_xml):
        """Valida el XML con el servicio DIAN"""
        try:
            # Implementar llamada al servicio de validación DIAN
            return {'is_valid': True, 'message': 'Documento válido'}
        except Exception as e:
            raise ValidationError(_('Error validando con DIAN: %s') % str(e))

    def _send_to_dian(self, signed_xml):
        """Envía el XML a la DIAN"""
        try:
            # Implementar envío a servicios DIAN
            return {'status': 'success', 'cune': '123456789', 'message': 'Documento recibido'}
        except Exception as e:
            raise ValidationError(_('Error enviando a DIAN: %s') % str(e))

    def _process_dian_response(self, electronic_doc, response):
        """Procesa la respuesta de la DIAN"""
        if response.get('status') == 'success':
            electronic_doc.write({
                'state': 'sent',
                'dian_response': json.dumps(response),
                'cune': response.get('cune'),
                'validation_date': fields.Datetime.now()
            })
        else:
            electronic_doc.write({
                'state': 'error',
                'dian_response': json.dumps(response)
            })

    def _generate_pdf(self, electronic_doc):
        """Genera la representación gráfica en PDF"""
        try:
            # Implementar generación de PDF
            pass
        except Exception as e:
            _logger.error("Error generando PDF: %s", str(e))

    def _get_result_action(self, electronic_doc):
        """Retorna la acción resultado"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.electronic.payroll',
            'res_id': electronic_doc.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_preview_xml(self):
        """Genera vista previa del XML"""
        self.ensure_one()
        
        try:
            # Crear documento temporal
            electronic_doc = self._create_electronic_document()
            
            # Generar XML
            xml_content = self._generate_xml_content(electronic_doc)
            
            # Actualizar vista previa
            self.preview_xml = xml_content.decode('utf-8')
            
            # Eliminar documento temporal
            electronic_doc.unlink()
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.payroll.electronic.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {'preview_mode': True}
            }
            
        except Exception as e:
            raise ValidationError(_('Error generando vista previa: %s') % str(e))