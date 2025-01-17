<script>
  import Date from "./Date.svelte";
  import Loader from "./Loader.svelte";
  import Nextbikes from "./Nextbikes.svelte";
  import Icon from "@iconify/svelte";
  import Timeline from "./Timeline.svelte";
  import Fireworks from "./Fireworks.svelte";
  import LocationFilter from "./LocationFilter.svelte";
  import { writable } from "svelte/store";
  import FocusKey from "svelte-focus-key";

  let showStats = false;
  let searchText = "";
  let normalizedSearchText = "";
  let searchElement;

  $: search(searchText);

  const selected_location_key = "location";
  const selected_location = writable(
    localStorage.getItem(selected_location_key) || "Poruba"
  );
  selected_location.subscribe((val) => {
    if (val === null) {
      localStorage.removeItem(selected_location_key);
    } else {
      localStorage.setItem(selected_location_key, val);
    }
  });

  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      ({ coords: { latitude: lat, longitude: lon } }) => {
        function distance(lat1, lon1, lat2, lon2) {
          const R = 6371 * 1000; // Earth radius in metres
          const deg2rad = (deg) => (deg * Math.PI) / 180;
          const d_lat = deg2rad(lat2 - lat1);
          const d_lon = deg2rad(lon2 - lon1);
          const a =
            Math.sin(d_lat / 2) * Math.sin(d_lat / 2) +
            Math.cos(deg2rad(lat1)) *
              Math.cos(deg2rad(lat2)) *
              Math.sin(d_lon / 2) *
              Math.sin(d_lon / 2);
          return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        }

        const places = [
          {
            lat: 49.7761644,
            lon: 18.2525182,
            distance: 1000,
            location: "Dubina",
          },
          {
            lat: 49.5931709,
            lon: 17.2643092,
            distance: 5000,
            location: "Olomouc",
          },
          {
            lat: 49.8051033,
            lon: 18.2361661,
            distance: 1500,
            location: "Zábřeh",
          },
        ];
        for (const place of places) {
          const d = distance(lat, lon, place.lat, place.lon);
          if (d <= place.distance) {
            $selected_location = place.location;
          }
        }
      }
    );
  }

  async function load(args) {
    //await new Promise((r) => setTimeout(r, 2000000));

    const res = await fetch("/lunch.json", args);
    const json = await res.json();
    if(json['error']) {
      throw json['error']
    }
    return json;
  }

  function refresh() {
    promise = load({ method: "POST" });
  }

  function toggleDarkMode() {
    const darkmode = +!document.body.classList.contains("dark");
    localStorage.setItem("darkmode", +darkmode.toString());
    document.body.classList[darkmode ? "add" : "remove"]("dark");
  }

  function normalizeString(str) {
    return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  function search(searchText) {
    normalizedSearchText = normalizeString(searchText);
  }

  function hasRestaurantMeal(restaurant, searchText) {
    return ((normalizeString(restaurant.name).includes(searchText))
          || ((restaurant.soups || []).some((s) => normalizeString(s.name).includes(searchText)))
          || ((restaurant.lunches || []).some((l) => normalizeString(l.name).includes(searchText)))
          || searchText === "")
  }

  function shallHighlight(meal, searchText) {
    return (normalizeString(meal).includes(normalizeString(searchText)) && searchText !== "");
  }

  let promise = load();
</script>

<div>
  {#await promise}
    <Loader />
  {:then { restaurants, last_fetch, fetch_count, first_access, access_count }}
    <div class="header">
      <Date />

      <div class="settings">
        <div class="settings-search">
          <input type="search" placeholder="Search (press '/' to focus)" bind:value={searchText} bind:this={searchElement} />
          <FocusKey element={searchElement} />
        </div>
        <div class="settings-buttons">
          <LocationFilter
            locations={[...new Set(restaurants.map((r) => r.location))]}
            bind:selected_location={$selected_location}
          />

          <a href="https://github.com/trnila/assistant">
            <Icon icon="bi:github" width="20" height="20" />
          </a>
          <button on:click={toggleDarkMode}>
            <Icon icon="ic:baseline-dark-mode" width="20" height="20" />
          </button>
          <button on:click={() => (showStats = !showStats)}>
            <Icon icon="bi:bar-chart-line-fill" width="20" height="20" />
          </button>
          <button on:click={refresh}>
            <Icon icon="zondicons:reload" width="20" height="20" />
          </button>
        </div>
      </div>
    </div>

    {#if access_count === 1}
      <Fireworks />
    {/if}

    {#if showStats}
      <Timeline
        data={restaurants}
        {last_fetch}
        {fetch_count}
        {first_access}
        {access_count}
      />
    {/if}

    {#if $selected_location == "Poruba"}
      <Nextbikes />
    {/if}

    {#each restaurants.filter((r) => (r.location == $selected_location || $selected_location == null)
        && hasRestaurantMeal(r, normalizedSearchText)) as restaurant}
      <div class="restaurant">
        <h2>
          <a href={restaurant.url}>
            {restaurant.name}
          </a>
        </h2>

        <ul>
          {#each restaurant.soups || [] as soup}
            <li class:search_highlight={shallHighlight(soup.name, normalizedSearchText)}>
              {#if soup.photo}
                <img src="{soup.photo}">
              {/if}
              <div>
                <strong>{soup.name}</strong>
                {#if soup.price}<span class="price">{soup.price} Kč</span>{/if}
              </div>
            </li>
          {/each}
        </ul>

        <ul>
          {#each restaurant.lunches || [] as lunch}
            <li class:ondras={lunch.name.toLowerCase().includes('ondráš')} class:search_highlight={shallHighlight(lunch.name, normalizedSearchText)}>
              {#if lunch.photo}
                <img src="{lunch.photo}">
                <div class="photo-zoom">
                  <div>
                    <img src="{lunch.photo}">
                    <div>
                      <strong>
                        {lunch.num}.
                        {lunch.name}
                      </strong>
                      {#if lunch.price}<span class="price">{lunch.price} Kč</span>{/if}
                      {#if lunch.ingredients}
                        <div>{lunch.ingredients}</div>
                      {/if}
                    </div>
                  </div>
                </div>
              {/if}
              <div>
                <strong>
                  {lunch.num}.
                  {lunch.name}
                </strong>
                {#if lunch.price}<span class="price">{lunch.price} Kč</span>{/if}
                {#if lunch.ingredients}
                  <div>{lunch.ingredients}</div>
                {/if}
              </div>
            </li>
          {:else}
            No lunch found.
          {/each}
        </ul>

        {#if restaurant.error}
          <pre>{restaurant.error}</pre>
        {/if}
      </div>
    {/each}
  {:catch error}
    <p>Load failed :(</p>
    <p>{error}</p>
  {/await}
</div>

<style>
  h2 {
    margin: 0px;
  }
  a {
    text-decoration: none;
    color: black;
  }
  ul {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  li {
    display: flex;
    gap: 5px;
  }

  li > img {
    width: 100px;
    padding-bottom: 5px;
  }

  img:hover + .photo-zoom {
    display: flex;
  }

  .photo-zoom {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    background: rgba(0, 0, 0, 0.8);
    width: 100vw;
    height: 100vh;
    pointer-events: none;
  }

  :global(body:not(.dark) .photo-zoom) {
    color: white;
  }

  .photo-zoom > div {
    margin: auto;
  }

  .photo-zoom img {
    max-width: 80vw;
    max-height: 80vh;
  }

  div.restaurant {
    margin-bottom: 10px;
  }

  .price {
    white-space: nowrap;
  }

  .header {
    top: 5px;
    right: 5px;
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
  }

  .settings {
    display: flex;
    gap: 5px;
    align-items: center;
  }

  button {
    padding: 0;
    background: transparent;
    border: 0;
    cursor: pointer;
  }

  .ondras {
    font-size: 3em;
    animation: blink 1s linear infinite;
  }
  .ondras strong {
    color: red !important;
  }

  @keyframes -global-blink {
    50% {opacity: 0.2}
  }
</style>
