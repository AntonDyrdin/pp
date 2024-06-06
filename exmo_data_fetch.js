const axios = require('axios');
const fs = require('fs');
const { DateTime } = require('luxon');
const moment = require('moment');

const symbol = 'USDT_RUB';
const resolution = 1; // 1 minute
const year = 2023;

// Start and end timestamps for April 2024 in Unix time
const startTime = DateTime.fromObject({ year, month: 7, day: 8, hour: 17, minute: 0, second: 0 }).toSeconds();
const endTime = DateTime.fromObject({ year, month: 12, day: 31, hour: 23, minute: 59, second: 0 }).toSeconds();

const baseUrl = 'https://api.exmo.com/v1.1/candles_history';
const outputFile = 'exmo_USDT_RUB-2023-2.csv';

async function fetchData() {
    let currentTime = startTime;
    const data = [];

    while (currentTime < endTime) {
        const toTime = Math.min(currentTime + 60 * 60, endTime); // Fetch data in hourly chunks
        await new Promise((resolve)=>{
            setTimeout(resolve, 1500);
        });
        console.log(new Date(currentTime*1000))
        try {
            const response = await axios.get(baseUrl, {
              timeout: 600000,
                params: {
                    symbol,
                    resolution,
                    from: currentTime,
                    to: toTime
                }
            });

            if (response.data && response.data.candles) {
                data.push(...response.data.candles);
            }

            currentTime = toTime;
        } catch (error) {
            console.error('Error fetching data:', error);
            break;
        }
    }

    return data;
}

function saveToCSV(data) {
//     const header = '<DATE>;<TIME>;<OPEN>;<HIGH>;<LOW>;<CLOSE>;<VOL>\n';
    const rows = data.map(candle => [
        moment(candle.t).utc().format('DDMMYY;HHmmss'),
        candle.o,
        candle.h,
        candle.l,
        candle.c,
        candle.v
    ].join(';')).join('\n');

    fs.writeFileSync(outputFile, rows);
    console.log(`Data saved to ${outputFile}`);
}

async function main() {
    const data = await fetchData();
    if (data.length > 0) {
        saveToCSV(data);
    } else {
        console.log('No data fetched');
    }
}

main();
