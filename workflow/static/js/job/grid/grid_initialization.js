import { createNewRow, getGridData } from '../deseralise_job_pricing.js';

export const sections = ['estimate', 'quote', 'reality'];
const workType = ['Time', 'Materials', 'Adjustments'];

export function initializeGrids(commonGridOptions, timeGridOptions, materialsGridOptions, adjustmentsGridOptions) {
    window.grids = {};

    console.log('Starting grid initialization...');

    sections.forEach(section => {
        console.log(`Initializing grids for section: ${section}`);
        workType.forEach(work => {
            console.log(`Creating grid for ${section} ${work}`);
            console.log('Grids below:');
            console.log(`commonGridOptions:`, commonGridOptions);
            console.log(`timeGridOptions:`, timeGridOptions);
            console.log('materialsGridOptions:', materialsGridOptions);
            console.log(`adjustmentsGridOptions:`, adjustmentsGridOptions);
            createGrid(section, work, commonGridOptions, timeGridOptions, materialsGridOptions, adjustmentsGridOptions);
        });
    });

    console.log('Grid initialization complete');
}

function createGrid(section, work, commonGridOptions, timeGridOptions, materialsGridOptions, adjustmentsGridOptions) {
    const gridType = `${work}Table`;
    const gridKey = `${section}${gridType}`;
    const gridElement = document.querySelector(`#${gridKey}`);

    const specificGridOptions = getSpecificGridOptions(section, work, gridType, timeGridOptions, materialsGridOptions, adjustmentsGridOptions);
    const rowData = getInitialRowData(section, gridType);

    const gridOptions = createGridOptions(section, gridType, gridKey, commonGridOptions, specificGridOptions, rowData);
    const gridInstance = agGrid.createGrid(gridElement, gridOptions);

    gridInstance.setGridOption('rowData', rowData);
}

function getSpecificGridOptions(section, work, gridType, timeGridOptions, materialsGridOptions, adjustmentsGridOptions) {
    let specificGridOptions;

    switch (gridType) {
        case 'TimeTable':
            specificGridOptions = getTimeTableOptions(section, timeGridOptions);
            break;
        case 'MaterialsTable':
            specificGridOptions = materialsGridOptions;
            break;
        case 'AdjustmentsTable':
            specificGridOptions = adjustmentsGridOptions;
            break;
    }

    return specificGridOptions;
}

function getTimeTableOptions(section, timeGridOptions) {
    if (section === 'reality') {
        return createRealityTimeTableOptions(timeGridOptions);
    }
    return createRegularTimeTableOptions(timeGridOptions);
}

function createRealityTimeTableOptions(timeGridOptions) {
    const options = JSON.parse(JSON.stringify(timeGridOptions));
    options.columnDefs.forEach(col => {
        col.editable = false;
        if (col.field === 'link') {
            col.cellRenderer = timeGridOptions.columnDefs.find(c => c.field === 'link').cellRenderer;
        }
    });
    options.columnDefs = options.columnDefs.filter(col => col.field !== '');
    return options;
}

function createRegularTimeTableOptions(timeGridOptions) {
    const options = { ...timeGridOptions };
    options.columnDefs = options.columnDefs.map(col => {
        if (col.field === 'link') {
            return { ...col, hide: true };
        }
        return col;
    });
    return options;
}

function getInitialRowData(section, gridType) {
    if (!latest_job_pricings_json) {
        throw new Error('latest_job_pricings_json must be loaded before grid initialization');
    }

    const sectionData = latest_job_pricings_json[`${section}_pricing`];
    if (!sectionData) {
        console.warn(`Data not found for section '${section}'. Assuming this is a new job.`);
    }

    let rowData = getGridData(section, gridType);
    if (rowData.length === 0) {
        rowData = [createNewRow(gridType)];
    }

    return rowData;
}

function createGridOptions(section, gridType, gridKey, commonGridOptions, specificGridOptions, rowData) {
    return {
        ...commonGridOptions,
        ...specificGridOptions,
        context: {
            section,
            gridType: `${gridType}`,
            gridKey: gridKey
        },
        rowData: rowData
    };
}

export function createTotalTables(revenueGridOptions, costGridOptions) {
    const revenueTableEl = document.querySelector('#revenueTable');
    if (revenueTableEl) {
        try {
            agGrid.createGrid(revenueTableEl, revenueGridOptions);
        } catch (error) {
            console.error('Error initializing revenue table:', error);
        }
    } else {
        console.error('Revenue table element not found');
    }

    const costsTableEl = document.querySelector('#costsTable');
    if (costsTableEl) {
        try {
            agGrid.createGrid(costsTableEl, costGridOptions);
        } catch (error) {
            console.error('Error initializing costs table:', error);
        }
    } else {
        console.error('Costs table element not found');
    }
}

export function checkGridInitialization() {
    const expectedGridCount = sections.length * workType.length + 2;
    const actualGridCount = Object.keys(window.grids).length;

    if (actualGridCount !== expectedGridCount) {
        console.error(`Not all grids were initialized. Expected: ${expectedGridCount}, Actual: ${actualGridCount}`);
    } else {
        console.log('All grids successfully initialized.');
    }
}