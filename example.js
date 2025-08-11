// Archivo JavaScript de prueba
class WebhookTest {
    constructor() {
        this.timestamp = new Date().toISOString();
    }
    
    triggerWebhook() {
        console.log(`Webhook triggered at: ${this.timestamp}`);
        return {
            status: 'success',
            message: 'Webhook test executed'
        };
    }
}

const test = new WebhookTest();
test.triggerWebhook();
