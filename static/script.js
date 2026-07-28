// Grab references to the HTML elements we need
const searchForm = document.getElementById('search-form');
const searchStatus = document.getElementById('search-status');
const resultsControls = document.getElementById('results-controls');
const resultsList = document.getElementById('results-list');
const filterSite = document.getElementById('filter-site');
const sortOrder = document.getElementById('sort-order');

// This holds the scholarships from the last search, so we can filter/sort
// them in the browser without asking the server again
let currentResults = [];

// Runs when the user submits the search form
searchForm.addEventListener('submit', async function (event) {
    event.preventDefault(); // stop the page from reloading

    const keyword = document.getElementById('keyword').value;
    const location = document.getElementById('location').value;

    searchStatus.textContent = 'Searching...';
    resultsList.innerHTML = '';
    resultsControls.style.display = 'none';

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keyword: keyword, location: location })
        });

        const data = await response.json();

        if (!response.ok) {
            searchStatus.textContent = data.error || 'Something went wrong. Please try again.';
            return;
        }

        if (data.results.length === 0) {
            searchStatus.textContent = data.message || 'No scholarships found.';
            currentResults = [];
            return;
        }

        searchStatus.textContent = `Found ${data.results.length} results.`;
        currentResults = data.results;

        fillFilterOptions(currentResults);
        resultsControls.style.display = 'block';
        renderResults(currentResults);

    } catch (error) {
        searchStatus.textContent = 'Could not connect to the server. Please check your connection and try again.';
    }
});

// Fill the "filter by source" dropdown with the unique websites from the results
function fillFilterOptions(results) {
    filterSite.innerHTML = '<option value="">All sources</option>';

    const uniqueSites = [...new Set(results.map(function (item) { return item.source_site; }))];

    uniqueSites.forEach(function (site) {
        const option = document.createElement('option');
        option.value = site;
        option.textContent = site;
        filterSite.appendChild(option);
    });
}

// Re-draw the results whenever the filter or sort dropdown changes
filterSite.addEventListener('change', applyFiltersAndSort);
sortOrder.addEventListener('change', applyFiltersAndSort);

function applyFiltersAndSort() {
    let filtered = currentResults;

    if (filterSite.value) {
        filtered = filtered.filter(function (item) {
            return item.source_site === filterSite.value;
        });
    }

    const sortValue = sortOrder.value;
    filtered = [...filtered].sort(function (a, b) {
        if (sortValue === 'title-asc') return a.title.localeCompare(b.title);
        if (sortValue === 'title-desc') return b.title.localeCompare(a.title);
        if (sortValue === 'source-asc') return a.source_site.localeCompare(b.source_site);
        return 0;
    });

    renderResults(filtered);
}

// Draw the scholarship cards on the page
function renderResults(results) {
    resultsList.innerHTML = '';

    results.forEach(function (item) {
        const card = document.createElement('div');
        card.className = 'result-card';

        const heading = document.createElement('h3');
        const link = document.createElement('a');
        link.href = item.link;
        link.target = '_blank';
        link.rel = 'noopener';
        link.textContent = item.title;
        heading.appendChild(link);

        const source = document.createElement('p');
        source.className = 'source';
        source.textContent = item.source_site;

        const snippet = document.createElement('p');
        snippet.textContent = item.snippet;

        const saveButton = document.createElement('button');
        saveButton.className = 'save-btn';
        saveButton.textContent = 'Save to Favorites';
        saveButton.addEventListener('click', function () {
            saveFavorite(item, saveButton);
        });

        card.appendChild(heading);
        card.appendChild(source);
        card.appendChild(snippet);
        card.appendChild(saveButton);

        resultsList.appendChild(card);
    });
}

// Send a scholarship to the server to be saved as a favorite
async function saveFavorite(item, button) {
    try {
        const response = await fetch('/api/favorites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item)
        });

        if (response.ok) {
            button.textContent = 'Saved!';
            button.disabled = true;
        } else {
            button.textContent = 'Could not save. Try again.';
        }
    } catch (error) {
        button.textContent = 'Could not save. Try again.';
    }
}
