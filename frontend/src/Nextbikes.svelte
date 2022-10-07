<style>
    ul {
        list-style: none;
        padding: 0;
        display: inline;
    }
    li {
        display: inline;
    }

    li:after {
        content: ', ';
    }

    ul li:last-child:after {
        content: '';
    }
</style>

<script>
async function load() {
    const res = await fetch('https://api.nextbike.net/maps/nextbike-live.json?city=271')
      const json = await res.json();

      const stations_map = [
        ['P-MSIC - Viva', 'Viva'],
        ['P-MSIC - Piano', 'Piano'],
        ['P-Koleje VŠB - vstup do lesoparku', 'Koleje bus'],
        ['P-koleje VŠB', 'Koleje'],
      ];

      const stations = stations_map.map(i => i[0]);
      const counts = Object.fromEntries(json.countries[0].cities[0].places.filter(i => stations.indexOf(i.name) >= 0).map(i => [i.name, i.bikes_available_to_rent]));

      return stations_map.filter(([key, name]) => counts[key]).map(([key, name]) => ({name, count: counts[key]}));
}
</script>

{#await load()}
    Loading
{:then stations}
    <strong>Nextbikes:</strong>
    <ul>
    {#each stations as station}
        <li>{station.name} ({station.count})</li>
    {/each}
    </ul>
{:catch}
    Failed to load data
{/await}