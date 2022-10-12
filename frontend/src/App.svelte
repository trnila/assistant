<script>
  import Date from "./Date.svelte";
  import Loader from "./Loader.svelte";
  import Nextbikes from "./Nextbikes.svelte";
  import Icon from "@iconify/svelte";
  import Timeline from "./Timeline.svelte";

  let showStats = false;

  async function load(args) {
    //await new Promise((r) => setTimeout(r, 2000000));

    const res = await fetch("/lunch.json", args);
    return await res.json();
  }

  function refresh() {
    promise = load({ method: "POST" });
  }

  function toggleDarkMode() {
    const darkmode = +!document.body.classList.contains("dark");
    localStorage.setItem("darkmode", +darkmode.toString());
    document.body.classList[darkmode ? "add" : "remove"]("dark");
  }

  let promise = load();
</script>

<Date />
<Nextbikes />

<div>
  <div class="buttons">
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

  {#await promise}
    <Loader />
  {:then { restaurants, last_fetch, fetch_count }}
    {#if showStats}
      <Timeline data={restaurants} {last_fetch} {fetch_count} />
    {/if}

    {#each restaurants as restaurant}
      <div class="restaurant">
        <h2>
          <a href={restaurant.url}>
            {restaurant.name}
          </a>
        </h2>

        <ul>
          {#each restaurant.soups || [] as soup}
            <li>
              <strong>{soup.name}</strong>
              {#if soup.price}<span class="price">{soup.price} Kč</span>{/if}
            </li>
          {/each}
        </ul>

        <ul>
          {#each restaurant.lunches || [] as lunch}
            <li>
              <strong>
                {#if lunch.num}{lunch.num}.{/if}
                {lunch.name}
              </strong>
              {#if lunch.price}<span class="price">{lunch.price} Kč</span>{/if}
              {#if lunch.ingredients}
                <div>{lunch.ingredients}</div>
              {/if}
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
  {/await}
</div>

<style>
  h2 {
    margin: 0px;
  }
  h2 a {
    text-decoration: none;
    color: black;
  }
  ul {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  div.restaurant {
    margin-bottom: 10px;
  }

  .price {
    white-space: nowrap;
  }

  .buttons {
    position: absolute;
    top: 5px;
    right: 5px;
  }

  button {
    padding: 0;
    background: transparent;
    border: 0;
    cursor: pointer;
  }
</style>
