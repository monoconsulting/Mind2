// JavaScript for test results page

let testData = [];
let filteredData = [];

document.addEventListener('DOMContentLoaded', function() {
    loadTestResults();
    setupEventListeners();
});

function setupEventListeners() {
    const searchInput = document.getElementById('search-input');
    const statusFilter = document.getElementById('status-filter');

    if (searchInput) {
        searchInput.addEventListener('input', filterResults);
    }

    if (statusFilter) {
        statusFilter.addEventListener('change', filterResults);
    }
}

async function loadTestResults() {
    try {
        const response = await fetch('data/test-results.json');
        if (response.ok) {
            const data = await response.json();
            testData = data.tests || [];
            filteredData = [...testData];
            updateTestResultsTable();
            updateTestStatistics();
        } else {
            console.log('No test results data file found');
            updateTestResultsTable();
            updateTestStatistics();
        }
    } catch (error) {
        console.log('Error loading test results:', error);
        updateTestResultsTable();
        updateTestStatistics();
    }
}

function updateTestResultsTable() {
    const tbody = document.getElementById('test-results-body');
    if (!tbody) return;

    if (filteredData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: 2rem; color: #7f8c8d;">
                    ${testData.length === 0 ? 'Inga testresultat tillgängliga än.' : 'Inga testresultat matchar dina filterkriterier.'}
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filteredData.map(test => `
        <tr>
            <td>${formatDate(test.timestamp)}</td>
            <td><strong>${test.testFile}</strong></td>
            <td>${test.description}</td>
            <td>
                <div class="progress-bar" style="width: 60px;">
                    <div class="progress-fill" style="width: ${test.successPercentage}%"></div>
                </div>
                ${test.successPercentage}%
            </td>
            <td>${test.score}/${test.maxScore}</td>
            <td><span class="status ${getStatusClass(test.successPercentage)}">${getStatusText(test.successPercentage)}</span></td>
            <td>
                ${test.reportLink ? `<a href="${test.reportLink}" target="_blank">Visa Rapport</a>` : 'Ej tillgänglig'}
            </td>
            <td>
                ${test.mediaLinks && test.mediaLinks.length > 0 ?
                    test.mediaLinks.map(link => `<a href="${link}" target="_blank">Media</a>`).join(', ') :
                    'Ej tillgänglig'
                }
            </td>
            <td>
                ${test.testFileLink ? `<a href="${test.testFileLink}" target="_blank">Visa Testfil</a>` : 'Ej tillgänglig'}
            </td>
        </tr>
    `).join('');
}

function updateTestStatistics() {
    const totalElement = document.getElementById('total-tests-count');
    const passedElement = document.getElementById('passed-tests-count');
    const failedElement = document.getElementById('failed-tests-count');
    const averageElement = document.getElementById('average-success-rate');

    const total = testData.length;
    const passed = testData.filter(test => test.successPercentage >= 90).length;
    const failed = testData.filter(test => test.successPercentage < 70).length;
    const average = total > 0 ? Math.round(testData.reduce((sum, test) => sum + test.successPercentage, 0) / total) : 0;

    if (totalElement) totalElement.textContent = total;
    if (passedElement) passedElement.textContent = passed;
    if (failedElement) failedElement.textContent = failed;
    if (averageElement) averageElement.textContent = `${average}%`;
}

function filterResults() {
    const searchTerm = document.getElementById('search-input')?.value.toLowerCase() || '';
    const statusFilter = document.getElementById('status-filter')?.value || '';

    filteredData = testData.filter(test => {
        const matchesSearch = !searchTerm ||
            test.testFile.toLowerCase().includes(searchTerm) ||
            test.description.toLowerCase().includes(searchTerm);

        const matchesStatus = !statusFilter ||
            getStatusClass(test.successPercentage) === statusFilter;

        return matchesSearch && matchesStatus;
    });

    updateTestResultsTable();
}

function clearFilters() {
    document.getElementById('search-input').value = '';
    document.getElementById('status-filter').value = '';
    filteredData = [...testData];
    updateTestResultsTable();
}

function formatDate(timestamp) {
    return new Date(timestamp).toLocaleString('sv-SE');
}

function getStatusClass(percentage) {
    if (percentage >= 90) return 'success';
    if (percentage >= 70) return 'warning';
    return 'error';
}

function getStatusText(percentage) {
    if (percentage >= 90) return 'Framgångsrik';
    if (percentage >= 70) return 'Delvis framgångsrik';
    return 'Misslyckad';
}

// Global function to add new test results (can be called by test agents)
window.addTestResult = function(testResult) {
    // Validate required fields
    const required = ['testFile', 'description', 'successPercentage', 'score', 'maxScore'];
    const missing = required.filter(field => testResult[field] === undefined || testResult[field] === null);

    if (missing.length > 0) {
        console.error('Missing required fields:', missing);
        return false;
    }

    // Add timestamp if not provided
    if (!testResult.timestamp) {
        testResult.timestamp = new Date().toISOString();
    }

    // Add to data
    testData.unshift(testResult); // Add to beginning of array
    filteredData = [...testData];

    // Update UI
    updateTestResultsTable();
    updateTestStatistics();

    // Save to file (in a real implementation, this would call a backend API)
    saveTestResults();

    return true;
};

function saveTestResults() {
    // In a real implementation, this would save to the server
    // For now, we'll just store in localStorage as a fallback
    try {
        localStorage.setItem('mind2-test-results', JSON.stringify({ tests: testData }));
        console.log('Test results saved to localStorage');
    } catch (error) {
        console.error('Error saving test results:', error);
    }
}