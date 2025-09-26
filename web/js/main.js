// Main JavaScript for Mind2 Documentation System

document.addEventListener('DOMContentLoaded', function() {
    updateSystemStats();
});

function updateSystemStats() {
    // Update last update time
    const lastUpdateElement = document.getElementById('last-update');
    if (lastUpdateElement) {
        const now = new Date();
        lastUpdateElement.textContent = now.toLocaleString('sv-SE');
    }

    // Load test statistics
    loadTestStats();
}

async function loadTestStats() {
    try {
        // Try to load test results data
        const response = await fetch('data/test-results.json');
        if (response.ok) {
            const data = await response.json();
            updateStatsFromData(data);
        } else {
            // If no data file exists, show default values
            updateStatsFromData({ tests: [] });
        }
    } catch (error) {
        console.log('No test data available yet:', error);
        updateStatsFromData({ tests: [] });
    }
}

function updateStatsFromData(data) {
    const totalTestsElement = document.getElementById('total-tests');
    const testSuccessRateElement = document.getElementById('test-success-rate');

    if (totalTestsElement) {
        totalTestsElement.textContent = data.tests ? data.tests.length : 0;
    }

    if (testSuccessRateElement && data.tests && data.tests.length > 0) {
        const successfulTests = data.tests.filter(test => test.status === 'success').length;
        const successRate = Math.round((successfulTests / data.tests.length) * 100);
        testSuccessRateElement.textContent = `${successRate}%`;
    } else if (testSuccessRateElement) {
        testSuccessRateElement.textContent = '0%';
    }
}

// Utility functions for test management
window.MindDocs = {
    addTestResult: function(testData) {
        // This function can be called by test agents to add results
        console.log('Adding test result:', testData);
        // Implementation would save to data/test-results.json
    },

    formatDate: function(date) {
        return new Date(date).toLocaleString('sv-SE');
    },

    getStatusClass: function(percentage) {
        if (percentage >= 90) return 'success';
        if (percentage >= 70) return 'warning';
        return 'error';
    }
};